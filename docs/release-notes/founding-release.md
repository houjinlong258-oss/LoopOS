# LoopOS 0.1.0 - Founding Release

**Release Date:** 2026-06-22
**Artifact SHA256:** `24ba6bced9d8b43748fdfd2b76dd3a4619f5355278081129852bc34473374fa5`
**Artifact Source Commit:** `df4a5dbea79d0cb3a002dc33f5e50609899b7e3c`

The artifact SHA is the digest of the entire ZIP. The internal `SHA256SUMS` file contains one
digest per packaged source file; it is not the ZIP digest. Verify both with:

```bash
python scripts/verify_release_artifact.py dist/loopos-0.1.0.zip --json
```

This operational release note and `docs/reports/latest-test-report.json` are intentionally
published beside, rather than embedded inside, the self-hashed artifact.

## Verification

- Python `zipfile` extraction: passed.
- System `tar` extraction: passed (`unzip` was unavailable in the verification environment).
- Internal `SHA256SUMS`: passed for all 391 packaged files.
- Artifact `.zip.sha256` sidecar: passed.
- Surrogate and non-ASCII archive path checks: passed.
- Extracted-source repackage: passed.
- Fresh-package Policy OS, convergence integration, Kernel/golden, and not-slow tests: passed.
- Fresh-package Deep Smoke: 10 checks passed within the 180-second global deadline.
- Verification environment: Windows 11, Python 3.13.2. No Linux CI matrix is claimed.

External providers, chat platforms, and production databases remain disabled in tests. A source
package has no `.git`; it can prove package integrity but cannot prove tag identity.
