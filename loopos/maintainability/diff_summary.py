"""Diff-based code change summary builder.

Parses unified diff text into a structured CodeChangeSummary
without executing git or touching the filesystem.
"""

from __future__ import annotations

import re

from loopos.maintainability.models import CodeChangeSummary, DiffParseStatus


def parse_diff(diff_text: str, *, run_id: str | None = None) -> CodeChangeSummary:
    """Parse unified diff text into a CodeChangeSummary."""
    if not diff_text.strip():
        return CodeChangeSummary(
            run_id=run_id,
            parse_status="empty",
            parse_warnings=["diff input is empty"],
        )

    changed_files: list[str] = []
    test_files: list[str] = []
    docs_files: list[str] = []
    config_files: list[str] = []
    added = 0
    removed = 0
    new_deps: list[str] = []
    new_apis: list[str] = []
    deleted_apis: list[str] = []
    risk_flags: list[str] = []
    parse_warnings: list[str] = []

    current_file: str | None = None
    saw_diff_header = False
    saw_hunk = False
    added_without_file = 0
    removed_without_file = 0

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            saw_diff_header = True
            current_file = None
            continue
        if line.startswith("@@"):
            saw_hunk = True
            continue
        # Detect file paths from diff headers
        file_match = re.match(r"^\+\+\+ b/(.+)$", line)
        if file_match:
            current_file = file_match.group(1)
            if current_file not in changed_files:
                changed_files.append(current_file)
            if _is_test_file(current_file):
                test_files.append(current_file)
            if _is_doc_file(current_file):
                docs_files.append(current_file)
            if _is_config_file(current_file):
                config_files.append(current_file)
            continue

        if line.startswith("+") and not line.startswith("+++"):
            added += 1
            content = line[1:]
            if current_file is None:
                added_without_file += 1
            # Detect new dependencies
            dep = _detect_dependency(content)
            if dep:
                new_deps.append(dep)
            # Detect new public APIs
            api = _detect_public_api(content)
            if api:
                new_apis.append(api)
            # Detect risk patterns
            risk = _detect_risk(content)
            if risk and risk not in risk_flags:
                risk_flags.append(risk)
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
            content = line[1:]
            if current_file is None:
                removed_without_file += 1
            api = _detect_public_api(content)
            if api:
                deleted_apis.append(api)

    parse_status: DiffParseStatus = "parsed"
    if not changed_files:
        has_diff_shape = saw_diff_header or saw_hunk or added or removed
        parse_status = "partial" if has_diff_shape else "non_diff"
        parse_warnings.append("no unified-diff file headers were parsed")
    elif added_without_file or removed_without_file:
        parse_status = "partial"
        parse_warnings.append("some changed lines appeared before a file header")
    if saw_diff_header and not changed_files:
        parse_status = "invalid"
        parse_warnings.append("diff headers were present but no +++ b/<path> headers were parsed")
    if risk_flags and not changed_files:
        parse_warnings.append("risk patterns were found in unparsed diff content")

    return CodeChangeSummary(
        run_id=run_id,
        parse_status=parse_status,
        parse_warnings=parse_warnings,
        changed_files=changed_files,
        added_lines=added,
        removed_lines=removed,
        modified_lines=min(added, removed),
        new_dependencies=new_deps,
        new_public_apis=new_apis,
        deleted_public_apis=deleted_apis,
        test_files_changed=test_files,
        docs_changed=docs_files,
        config_files_changed=config_files,
        risk_flags=risk_flags,
    )


def _is_test_file(path: str) -> bool:
    return "test" in path.lower() and path.endswith(".py")


def _is_doc_file(path: str) -> bool:
    return path.lower().endswith((".md", ".rst", ".txt")) or "docs/" in path.lower()


def _is_config_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1].lower()
    return name in {
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
        ".env",
        ".env.example",
        "Makefile",
        "Dockerfile",
        "docker-compose.yml",
    } or name.endswith((".yaml", ".yml", ".toml", ".ini", ".cfg"))


def _detect_dependency(line: str) -> str | None:
    """Detect common dependency patterns in added lines."""
    line = line.strip()
    # import statements
    match = re.match(r"^(?:from|import)\s+(\w+)", line)
    if match:
        module = match.group(1)
        # Only flag third-party (skip stdlib and project)
        if module not in _STDLIB_PREFIXES and module != "loopos":
            return module
    # pyproject.toml / requirements.txt style
    match = re.match(r'^[\s"]*(\w[\w-]*)[\s><=~!]', line)
    if match and ("dependencies" in line.lower() or ">=" in line or "==" in line):
        return match.group(1)
    return None


def _detect_public_api(line: str) -> str | None:
    """Detect function/class definitions that form public API."""
    line = line.strip()
    match = re.match(r"^(?:def|class)\s+([A-Za-z_]\w*)", line)
    if match:
        name = match.group(1)
        if not name.startswith("_"):
            return name
    return None


def _detect_risk(line: str) -> str | None:
    """Detect risk patterns in added lines."""
    line_lower = line.lower().strip()
    if re.search(r"\bos\.system\s*\(", line):
        return "os.system_call"
    if re.search(r"\bsubprocess\.(call|run|Popen)\s*\(", line):
        return "subprocess_call"
    if "eval(" in line or "exec(" in line:
        return "eval_exec"
    if re.search(r"\brm\s+-rf\b", line_lower):
        return "rm_rf"
    if "sudo " in line_lower:
        return "sudo_usage"
    if re.search(r"(api_key|secret|password|token)\s*=\s*[\"']", line_lower):
        return "hardcoded_secret"
    if "chmod" in line_lower and "777" in line:
        return "chmod_777"
    return None


_STDLIB_PREFIXES = {
    "os", "sys", "re", "json", "pathlib", "datetime", "typing",
    "uuid", "hashlib", "collections", "functools", "itertools",
    "dataclasses", "enum", "abc", "io", "math", "shutil",
    "tempfile", "textwrap", "unittest", "logging", "copy",
    "contextlib", "warnings", "traceback", "inspect", "types",
    "importlib", "pkgutil", "sqlite3", "csv", "configparser",
    "argparse", "string", "struct", "codecs", "base64",
    "secrets", "hmac", "urllib", "http", "socket", "email",
    "html", "xml", "multiprocessing", "threading", "queue",
    "signal", "subprocess", "glob", "fnmatch", "stat",
    "platform", "pprint", "difflib", "time", "calendar",
    "random", "decimal", "fractions", "operator",
    "__future__",
}
