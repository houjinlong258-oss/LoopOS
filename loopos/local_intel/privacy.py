"""Privacy-first workspace indexing rules."""

from __future__ import annotations

from pathlib import Path

BLOCKED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".loopos",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build", "vendor",
}
TEXT_EXTENSIONS = {
    ".py", ".pyi", ".md", ".txt", ".rst", ".json", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".sh", ".ps1", ".js", ".jsx", ".ts", ".tsx", ".html", ".css",
    ".sql", ".xml", ".csv",
}
MAX_FILE_BYTES = 1024 * 1024


def is_private_path(path: Path, workspace: Path) -> bool:
    try:
        relative = path.resolve().relative_to(workspace.resolve())
    except ValueError:
        return True
    if any(part in BLOCKED_DIRS for part in relative.parts[:-1]):
        return True
    name = path.name.lower()
    if name == ".env" or name.startswith(".env."):
        return True
    if name in {"id_rsa", "id_ed25519", "credentials", "credentials.json", "secrets.json"}:
        return True
    if path.suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".crt"}:
        return True
    return any(marker in name for marker in ("private_key", "secret", "credential"))


def is_indexable_text(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size <= MAX_FILE_BYTES and path.suffix.lower() in TEXT_EXTENSIONS
    except OSError:
        return False
