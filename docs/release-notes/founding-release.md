# LoopOS 0.1.0 - Founding Release

**Release Date:** pending final verification
**Artifact SHA256:** PENDING_FINAL_BUILD

The artifact SHA is the digest of the entire ZIP. The internal `SHA256SUMS` file contains one
digest per packaged source file; it is not the ZIP digest. Verify both with:

```bash
python scripts/verify_release_artifact.py dist/loopos-0.1.0.zip --json
```

This operational release note and `docs/reports/latest-test-report.json` are intentionally
published beside, rather than embedded inside, the self-hashed artifact.

## Verification
- Verification status: release candidate until the final clean-package matrix completes.
- External providers, chat platforms, and production databases remain disabled in tests.
- A source package has no `.git`; it can be package-ready but cannot prove tag identity.
