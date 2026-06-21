"""Compute mode and plugin registry commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

from loopos.compute import ComputeMode, ComputeModeStore, ComputeRouter
from loopos.registry import PluginRegistry, PluginType, audit_manifest, load_manifest


def mode_command(
    action: str = "status",
    value: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
    private_data: bool = False,
    sanitized: bool = False,
    cloud_consent: bool = False,
) -> int:
    store = ComputeModeStore(Path(data_dir) / "compute-mode.json")
    if action == "set":
        if value not in {"privacy-local", "hybrid", "cloud-power"}:
            print("mode must be privacy-local, hybrid, or cloud-power", file=sys.stderr)
            return 1
        config = store.set(cast(ComputeMode, value))
    elif action == "status":
        config = store.load()
    else:
        print(f"Unknown mode action: {action}", file=sys.stderr)
        return 1
    decision = ComputeRouter().decide(
        config.mode,
        private_data=private_data,
        sanitized=sanitized,
        cloud_consent=cloud_consent,
    )
    print(decision.model_dump_json(indent=2))
    return 0


def registry_command(
    action: str = "list",
    value: str | None = None,
    *,
    plugin_type: str | None = None,
    data_dir: str | Path = ".loopos",
) -> int:
    registry = PluginRegistry(Path(data_dir) / "registry")
    typed = cast(PluginType, plugin_type) if plugin_type else None
    try:
        if action == "list":
            payload: object = [item.model_dump(mode="json") for item in registry.list(plugin_type=typed)]
        elif action == "search":
            payload = [item.model_dump(mode="json") for item in registry.search(value or "", plugin_type=typed)]
        elif action == "install" and value:
            manifest, audit = registry.install(value)
            payload = {"manifest": manifest.model_dump(mode="json"), "audit": audit.model_dump(mode="json")}
        elif action == "audit" and value:
            path = Path(value)
            payload = (
                audit_manifest(load_manifest(path)).model_dump(mode="json")
                if path.is_file()
                else registry.audit(value).model_dump(mode="json")
            )
        else:
            print(f"Unknown or incomplete registry action: {action}", file=sys.stderr)
            return 1
    except (KeyError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
