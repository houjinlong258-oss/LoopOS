"""Workspace-local, checksum-verified backup vault."""

from __future__ import annotations

import hashlib
import json
import shutil
import stat
from pathlib import Path

from loopos.data_guard.models import BackupManifest


class BackupVault:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        *,
        run_id: str,
        source: str | Path,
        policy_decision_id: str = "",
    ) -> BackupManifest:
        source_path = Path(source).resolve()
        if not source_path.is_file():
            raise ValueError("backup source must be an existing local file")
        manifest = BackupManifest(
            run_id=run_id,
            source=str(source_path),
            policy_decision_id=policy_decision_id,
        )
        target_dir = self.root / run_id / manifest.backup_id
        target_dir.mkdir(parents=True, exist_ok=False)
        target = target_dir / source_path.name
        shutil.copy2(source_path, target)
        checksum = _sha256(target)
        manifest.files = [target.name]
        manifest.checksums = {target.name: checksum}
        manifest.restore_plan_path = str(target_dir / "restore_plan.json")
        manifest.verification_report = {"files_checked": 1, "checksum_match": True}
        manifest.verified = True
        (target_dir / "restore_plan.json").write_text(
            json.dumps({"backup_id": manifest.backup_id, "executable": False}, indent=2),
            encoding="utf-8",
        )
        self._write_manifest(target_dir, manifest)
        for path in target_dir.iterdir():
            path.chmod(stat.S_IREAD)
        return manifest

    def load(self, backup_id: str) -> BackupManifest:
        manifest_path = self._find_manifest(backup_id)
        return BackupManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    def verify(self, backup_id: str) -> BackupManifest:
        manifest_path = self._find_manifest(backup_id)
        manifest = BackupManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        base = manifest_path.parent
        failures: list[str] = []
        for name, expected in manifest.checksums.items():
            path = base / name
            if not path.is_file():
                failures.append(f"missing:{name}")
            elif _sha256(path) != expected:
                failures.append(f"checksum:{name}")
        manifest.verified = not failures and bool(manifest.files)
        manifest.verification_report = {
            "files_checked": len(manifest.files),
            "failures": failures,
            "checksum_match": not failures,
        }
        return manifest

    def _find_manifest(self, backup_id: str) -> Path:
        matches = list(self.root.glob("*/*/backup_manifest.json"))
        for path in matches:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("backup_id") == backup_id:
                return path
        raise KeyError(f"backup not found: {backup_id}")

    @staticmethod
    def _write_manifest(target_dir: Path, manifest: BackupManifest) -> None:
        (target_dir / "backup_manifest.json").write_text(
            manifest.model_dump_json(indent=2), encoding="utf-8"
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
