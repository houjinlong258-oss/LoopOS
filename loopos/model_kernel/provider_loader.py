"""Provider profile YAML loader."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from loopos.model_kernel.models import ProviderProfile


def load_provider_profiles(paths: Iterable[str | Path]) -> list[ProviderProfile]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - depends on environment setup.
        raise RuntimeError("PyYAML is required to load provider profiles") from exc

    profiles: list[ProviderProfile] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        files = sorted([*path.rglob("*.yaml"), *path.rglob("*.yml")]) if path.is_dir() else [path]
        for file in files:
            payload = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
            if isinstance(payload, dict) and "providers" in payload:
                rows = payload["providers"]
            else:
                rows = [payload]
            if not isinstance(rows, list):
                raise ValueError(f"provider profile file must contain a profile or providers list: {file}")
            profiles.extend(ProviderProfile.model_validate(row) for row in rows)
    return profiles

