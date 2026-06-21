# LoopOS pre-release checklist

This is the human-readable checklist the release shepherd follows
before tagging a release.  It mirrors the items enforced by
`scripts/check_release_clean.py` and exercised by
`tests/test_release_hygiene.py`.

## 1. Branch & tree

- [ ] working tree clean (`git status --porcelain` is empty)
- [ ] on the release branch (not on a feature branch)
- [ ] all intended commits pushed and reviewed

## 2. Hygiene

- [ ] `python scripts/check_release_clean.py` exits 0
- [ ] no `.git` / `.venv` / `.loopos` / caches / `__pycache__` in the tree
- [ ] no third-party source snapshots (OpenHands / langgraph / letta /
      zep / projectmem / hermes-agent-*) in the tree
- [ ] no local planning notes (`task_plan.md` / `findings.md` /
      `progress.md`) in the tree
- [ ] no absolute dev paths (`D:\\LoopOS` / `/home/.../LoopOS`) in source

## 3. Tests & types

- [ ] `pytest` passes
- [ ] `ruff check .` passes
- [ ] `mypy .` passes
- [ ] `tests/acceptance_founding/` passes end-to-end

## 4. Required files

- [ ] `LICENSE` present
- [ ] `README.md` present and up to date
- [ ] `CHANGELOG.md` bumped
- [ ] `AGENTS.md` present
- [ ] `ROADMAP.md` present and reflects this release
- [ ] `CONTRIBUTING` / `SECURITY` / `CODE_OF_CONDUCT` present
- [ ] `pyproject.toml` version bumped

## 5. Packaging smoke

- [ ] `python scripts/package_release.py --version <X> --output dist`
      exits 0 and produces `loopos-<X>.zip`
- [ ] `MANIFEST.txt` and `SHA256SUMS` written alongside the staging dir
- [ ] `unzip -l dist/loopos-<X>.zip` shows no forbidden paths

## 6. Post-build verification

- [ ] extract the zip into a fresh temp dir
- [ ] `python scripts/check_release_clean.py --source <extracted>` exits 0
- [ ] `pytest` passes against the extracted tree

## 7. Final sign-off

- [ ] SHA256 of the zip recorded in the release notes
- [ ] tag created: `git tag -s v<X>`
- [ ] release notes published
