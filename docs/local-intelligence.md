# Local Workspace Intelligence

The local index stores allowed UTF-8 text and file metadata in SQLite. It excludes `.env`, key and
credential files, `.git`, dependencies, caches, binaries, and files larger than 1 MiB. Search is
deterministic lexical ranking and does not call a model or network service.

Use `loopos index build`, `loopos index status`, `loopos search QUERY`, and
`loopos files find QUERY`. Compute modes are `privacy-local`, `hybrid`, and `cloud-power`; private
inputs remain local in every mode, and cloud-power requires explicit consent.
