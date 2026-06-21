"""CLI commands for release hygiene and packaging.

Subcommands:

    loopos release check          Run the hygiene checker against the repo.
    loopos release package        Build a clean release artifact.
    loopos release checklist      Print the pre-release checklist.
"""

from __future__ import annotations

import json
import sys

from loopos.release import (
    check_release_clean,
    check_release_readiness,
    package_release,
    render_readiness,
)


_CHECKLIST_LINES: tuple[str, ...] = (
    "LoopOS pre-release checklist",
    "============================",
    "",
    "1. Branch & tree",
    "   [ ] working tree clean (git status --porcelain is empty)",
    "   [ ] on the release branch (not on a feature branch)",
    "   [ ] all intended commits pushed and reviewed",
    "",
    "2. Hygiene",
    "   [ ] `python scripts/check_release_clean.py` exits 0",
    "   [ ] no .git / .venv / .loopos / caches / __pycache__ in the tree",
    "   [ ] no third-party source snapshots (OpenHands / langgraph / letta /",
    "       zep / projectmem / hermes-agent-*) in the tree",
    "   [ ] no local planning notes (task_plan.md / findings.md / progress.md)",
    "       in the tree",
    "   [ ] no absolute developer workspace paths in source",
    "",
    "3. Tests & types",
    "   [ ] pytest passes",
    "   [ ] ruff check . passes",
    "   [ ] mypy . passes",
    "   [ ] tests/acceptance_founding/ passes end-to-end",
    "",
    "4. Required files",
    "   [ ] LICENSE present",
    "   [ ] README.md present and up to date",
    "   [ ] CHANGELOG.md bumped",
    "   [ ] AGENTS.md present",
    "   [ ] ROADMAP.md present and reflects this release",
    "   [ ] CONTRIBUTING / SECURITY / CODE_OF_CONDUCT present",
    "   [ ] pyproject.toml version bumped",
    "",
    "5. Packaging smoke",
    "   [ ] `python scripts/package_release.py --version <X> --output dist`",
    "       exits 0 and produces loopos-<X>.zip",
    "   [ ] MANIFEST.txt and SHA256SUMS written alongside the staging dir",
    "   [ ] unzip -l dist/loopos-<X>.zip shows no forbidden paths",
    "",
    "6. Post-build verification",
    "   [ ] extract the zip into a fresh temp dir",
    "   [ ] `python scripts/check_release_clean.py --source <extracted>` exits 0",
    "   [ ] pytest passes against the extracted tree",
    "",
    "7. Final sign-off",
    "   [ ] SHA256 of the zip recorded in the release notes",
    "   [ ] tag created: git tag -s v<X>",
    "   [ ] release notes published",
)


def release_command(
    action: str = "check",
    *,
    version: str = "0.1.0",
    source: str = ".",
    output: str = "dist",
    no_zip: bool = False,
    strict: bool = False,
    ignore_local_only: bool = False,
    strict_source: bool = False,
    deep: bool = False,
    json_output: bool = False,
    target: str = "founding-preview",
) -> int:
    """Entry point for ``loopos release <action>``."""

    if action == "check":
        return _check(
            source=source,
            strict=strict,
            ignore_local_only=ignore_local_only,
            json_output=json_output,
        )
    if action == "package":
        return _package(
            version=version,
            source=source,
            output=output,
            make_zip=not no_zip,
            json_output=json_output,
        )
    if action == "checklist":
        return _checklist(json_output=json_output)
    if action == "readiness":
        report = check_release_readiness(
            source,
            target=target,
            strict_source=strict_source,
            deep=deep,
        )
        if json_output:
            print(report.model_dump_json(indent=2))
        else:
            print(render_readiness(report))
        return 0 if report.ready else 1
    print(f"Unknown release action: {action}", file=sys.stderr)
    return 1


def _check(
    *,
    source: str,
    strict: bool,
    ignore_local_only: bool,
    json_output: bool,
) -> int:
    report = check_release_clean(source, ignore_local_only=ignore_local_only)
    if json_output:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"source:       {report.source}")
        print(f"ok:           {str(report.ok).lower()}")
        print(f"scanned_files: {report.scanned_files}")
        print(f"scanned_dirs:  {report.scanned_dirs}")
        print(f"errors:        {len(report.errors)}")
        for f in report.errors:
            loc = f" {f.path}:" if f.path else ""
            print(f"  [error] {f.code}{loc} {f.message}")
        print(f"warnings:      {len(report.warnings)}")
        for f in report.warnings:
            loc = f" {f.path}:" if f.path else ""
            print(f"  [warn]  {f.code}{loc} {f.message}")
    if not report.ok:
        return 1
    if strict and report.warnings:
        return 1
    return 0


def _package(
    *,
    version: str,
    source: str,
    output: str,
    make_zip: bool,
    json_output: bool,
) -> int:
    report = package_release(
        version=version,
        source=source,
        output=output,
        make_zip=make_zip,
    )
    if json_output:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"version:      {report.version}")
        print(f"source:       {report.source}")
        print(f"staging_dir:  {report.staging_dir}")
        print(f"manifest:     {report.manifest_path}")
        print(f"sha256:       {report.sha256_path}")
        if report.zip_path:
            print(f"zip:          {report.zip_path}")
        print(f"copied_files: {report.copied_files}")
        print(f"errors:       {len(report.errors)}")
        if report.errors:
            for err in report.errors:
                print(f"  [error] {err}")
        print(f"hygiene_findings: {len(report.hygiene_errors)}")
        for f in report.hygiene_errors:
            loc = f" {f.path}:" if f.path else ""
            print(f"  [hygiene] {f.code}{loc} {f.message}")
    return 1 if report.errors else 0


def _checklist(*, json_output: bool) -> int:
    if json_output:
        print(json.dumps({"lines": list(_CHECKLIST_LINES)}, indent=2))
    else:
        for line in _CHECKLIST_LINES:
            print(line)
    return 0
