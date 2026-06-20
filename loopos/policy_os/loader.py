"""Policy pack loading."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from loopos.policy_os.models import PolicyPack


def load_policy_pack(path: str | Path) -> PolicyPack:
    """Load one YAML policy pack."""

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - depends on environment setup.
        raise RuntimeError("PyYAML is required to load Policy OS packs") from exc

    policy_path = Path(path)
    with policy_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"policy pack must be a mapping: {policy_path}")
    return PolicyPack.model_validate(payload)


def load_policy_packs(paths: Iterable[str | Path]) -> list[PolicyPack]:
    """Load all YAML packs from files or directories."""

    packs: list[PolicyPack] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        if path.is_dir():
            for policy_file in sorted([*path.rglob("*.yaml"), *path.rglob("*.yml")]):
                packs.append(load_policy_pack(policy_file))
        else:
            packs.append(load_policy_pack(path))
    return packs


def pack_to_dict(pack: PolicyPack) -> dict[str, Any]:
    """Return a JSON-compatible pack dictionary for CLI output."""

    return pack.model_dump(mode="json")
