# LoopOS release hygiene

This document explains the rules enforced by the release-hygiene scripts
and how to use them.  The scripts are the canonical implementation of
the rules; this document is the human-readable companion.

## Motivation

LoopOS is shipped as a source tree, not as a wheel.  The release
artifact must be a clean, reproducible copy of the source — free of:

- VCS internals (`.git/`)
- Virtualenvs (`.venv/`)
- Local execution state (`.loopos/`, `.loopos-*/`)
- Build caches (`__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`,
  `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`)
- Build artifacts (`dist/`, `build/`, `*.egg-info/`)
- Third-party source snapshots kept locally as architectural references
  (`OpenHands-*/`, `langgraph-*/`, `letta-*/`, `zep-main/`,
  `projectmem-*/`, `hermes-agent-*/`)
- Local-only planning notes (`task_plan.md`, `findings.md`,
  `progress.md`) — these are gitignored and must not leak.

And it MUST contain the top-level governance / contract files required
for an open-source release: `LICENSE`, `README.md`, `CHANGELOG.md`,
`AGENTS.md`, `ROADMAP.md`, `CONTRIBUTING.md`, `SECURITY.md`,
`CODE_OF_CONDUCT.md`, `pyproject.toml`.

## Scripts

### `scripts/check_release_clean.py`

Runs the hygiene checker against the source tree.  Exits 0 if clean, 1
if any blocked violation is found, 2 on usage error.

```bash
python scripts/check_release_clean.py                 # check current dir
python scripts/check_release_clean.py --source path   # check a different dir
python scripts/check_release_clean.py --json          # JSON report
python scripts/check_release_clean.py --strict        # warnings -> errors
```

The `--strict` flag promotes warnings (e.g. leaked absolute dev paths)
to errors.  Use it in CI; use the default in local development.

### `scripts/package_release.py`

Stages a clean copy of the source tree into
`<output>/loopos-<version>/`, writes a sorted `MANIFEST.txt` and a
sorted `SHA256SUMS`, and optionally zips the staged tree into
`loopos-<version>.zip`.

```bash
python scripts/package_release.py --version 0.1.0 --output dist
python scripts/package_release.py --version 0.1.0 --output dist --no-zip
python scripts/package_release.py --version 0.1.0 --output dist --json
```

The script refuses to overwrite an existing staging directory.  Delete
the staging dir before re-running, or use a fresh output dir.

## CLI

Both scripts are also available as the `loopos release` command group:

```bash
loopos release check                 # check current dir
loopos release check --source path   # check a different dir
loopos release check --strict        # warnings -> errors
loopos release check --json          # JSON report

loopos release package --version 0.1.0 --output dist
loopos release package --version 0.1.0 --output dist --no-zip

loopos release checklist             # print the pre-release checklist
```

## Programmatic API

The same logic is exposed via `loopos.release` so other tools (CI,
release automation) can consume it without shelling out:

```python
from loopos.release import check_release_clean, package_release

report = check_release_clean(".")
if not report.ok:
    for finding in report.errors:
        print(finding.code, finding.path, finding.message)

pkg = package_release(version="0.1.0", source=".", output="dist", make_zip=True)
print(pkg.staging_dir, pkg.zip_path, len(pkg.errors))
```

## What the checker looks for

| Code                    | Severity | Meaning                                                  |
| ----------------------- | -------- | -------------------------------------------------------- |
| `SOURCE_MISSING`        | error    | The source path is not a directory.                       |
| `MISSING_REQUIRED_FILE` | error    | A required top-level file (e.g. `LICENSE`) is missing.   |
| `BLOCKED_DIR`           | error    | A blocked directory (e.g. `.git/`) was found.             |
| `BLOCKED_FILE`          | error    | A blocked file (e.g. `task_plan.md`, `*.pyc`) was found. |
| `LEAKED_DEV_PATH`       | warning  | An absolute dev path (e.g. `D:\LoopOS`) was found in text.|

## CI integration

A minimal CI gate looks like:

```yaml
- name: Release hygiene
  run: python scripts/check_release_clean.py --strict

- name: Package release
  run: |
    python scripts/package_release.py --version ${{ github.ref_name }} --output dist --json \
      > dist/package-report.json

- name: Verify extracted artifact
  run: |
    python -m venv /tmp/verify
    /tmp/verify/bin/python -m pip install --upgrade pip
    /tmp/verify/bin/python -m pip install dist/loopos-*.zip
    /tmp/verify/bin/python -m pytest --pyargs loopos
```

## Edge cases

- **Empty blocked directories**: an empty `.git/` at the top level is
  still flagged.  The checker iterates top-level entries explicitly so
  it catches directories that `os.walk` would otherwise visit without
  emitting any file findings.
- **Caches inside the package**: `loopos/__pycache__/` is flagged with
  the directory name (`__pycache__`) even when the offending file
  inside has a `.pyc` extension.  The directory finding wins so the
  report stays compact.
- **Binary files**: the leaked-path scanner reads up to 2 KiB of each
  file looking for a NUL byte; if it finds one, the file is treated as
  binary and skipped.
- **Existing staging dir**: `package_release` returns an error rather
  than overwriting.  The caller must `rm -rf` first.
