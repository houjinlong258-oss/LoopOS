# Local Workspace Intelligence

The local index stores allowed UTF-8 text and file metadata in SQLite. It excludes `.env`, key and
credential files, `.git`, dependencies, caches, binaries, and files larger than 1 MiB. Search is
deterministic lexical ranking and does not call a model or network service.

`loopos index build` indexes both allowed text and Python AST symbols/imports. Use:

```bash
loopos index status
loopos index symbols
loopos search "backup manifest"
loopos search symbols BackupGuard
loopos files find gateway
loopos files explain loopos/data_guard/sqlite_adapter.py
```

Compute modes are `privacy-local`, `hybrid`, and `cloud-power`; private inputs remain local in
every mode, and cloud-power requires explicit consent. Symbol extraction is Python-only and does
not execute imported modules.
