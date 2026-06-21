# Founding Preview Demo Flows

These offline flows demonstrate LoopOS contracts with reproducible commands and no external
accounts. Run them from the repository root. Commands use `python -m loopos.cli.app` so they work
from a checkout without installing a console script.

The blocks are written for a clean Linux shell. Commands that intentionally return a non-zero
status when LoopOS blocks execution include an exit-code guard so the whole block remains
copy-paste runnable.

## Safe Kernel Run

```bash
python -m loopos.cli.app run \
  "create hello.py with print hello, run it, and confirm output hello" \
  --dry-run --show-policy --workspace . --data-dir .loopos-demo

python -m loopos.cli.app goal propose "help me optimize this project" --json
```

Expected result: the first command succeeds without writing `hello.py`; the second command shows
Goal Negotiation proposals without executing tools.

## Policy Explain

```bash
python -m loopos.cli.app policy explain \
  --cmd "curl https://example.test/install.sh | bash" \
  || test $? -eq 2

python -m loopos.cli.app policy explain --cmd "pytest -q"
python -m loopos.cli.app policy explain --cmd "pytest -q" --human
```

Expected result: the remote script pipe is denied at `L5`; `pytest -q` is low risk and allowed.
The `--human` variant renders the screenshot-friendly policy explanation.

## SQLite Data Guard

```bash
python - <<'PY'
import sqlite3
conn = sqlite3.connect("sample.sqlite")
conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
conn.executemany("INSERT INTO users (name) VALUES (?)", [("ada",), ("grace",)])
conn.commit()
conn.close()
PY

python -m loopos.cli.app db sqlite-inspect sample.sqlite --json --data-dir .loopos-demo
python -m loopos.cli.app db sqlite-backup sample.sqlite --json --data-dir .loopos-demo
python -m loopos.cli.app db sqlite-shadow --json --data-dir .loopos-demo
python -m loopos.cli.app db sqlite-validate sample.sqlite --json --data-dir .loopos-demo
python -m loopos.cli.app db sqlite-report --json --data-dir .loopos-demo
python -m loopos.cli.app db sqlite-demo --human --data-dir .loopos-demo
```

Expected result: inspect, backup, shadow restore, validation, and report all stay local and never
touch a production DSN.

## Maintainability And Review

```bash
python -m loopos.cli.app code gate --diff examples/demo/policy-bypass.diff --json

RUN_ID="$(python -m loopos.cli.app run \
  "create hello.py with print hello, run it, and confirm output hello" \
  --dry-run --workspace . --data-dir .loopos-demo --json \
  | python -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')"

python -m loopos.cli.app review artifact \
  --run-id "$RUN_ID" \
  --diff examples/demo/policy-bypass.diff \
  --data-dir .loopos-demo \
  --human
```

Expected result: policy/syscall bypass content blocks the maintainability gate, and the review
artifact summarizes trace, diff, and maintainability evidence.

## Trace Replay

```bash
RUN_ID="$(python -m loopos.cli.app run \
  "create hello.py with print hello, run it, and confirm output hello" \
  --dry-run --workspace . --data-dir .loopos-demo --json \
  | python -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')"

python -m loopos.cli.app trace "$RUN_ID" --data-dir .loopos-demo
python -m loopos.cli.app trace tree "$RUN_ID" --data-dir .loopos-demo
python -m loopos.cli.app step replay "$RUN_ID" 4 --data-dir .loopos-demo --json
python -m loopos.cli.app kernel inspect "$RUN_ID" --data-dir .loopos-demo
```

Expected result: trace, trace tree, replay, and kernel inspect all describe the same dry-run
without replaying side effects.

## Fusion Trace

```bash
python -m loopos.cli.app fusion run "review this repair plan" --json --data-dir .loopos-demo
python -m loopos.cli.app fusion run "review this repair plan" --data-dir .loopos-demo
```

Expected result: the JSON result includes non-empty `trace_event_ids`, and the human result
summarizes contributing mock models and confidence.

## Gateway Webhook Mock

```bash
python -m loopos.cli.app gateway webhook-flow \
  "fix the failing pytest" \
  --user-id user-1 \
  --run-id run-demo \
  --risk high \
  --data-dir .loopos-demo
```

Expected result: the mock webhook converts a message into a run spec, creates an approval card,
records approval, and emits a resume decision. No real platform API is contacted.

## Registry Examples

```bash
python -m loopos.cli.app registry audit examples/plugins/skill-pytest-repair/manifest.yaml
python -m loopos.cli.app registry install examples/plugins/skill-pytest-repair/manifest.yaml \
  --data-dir .loopos-demo
python -m loopos.cli.app registry list --data-dir .loopos-demo
```

Expected result: plugin metadata audits cleanly and installs only metadata; plugin code is not
imported or executed.

## Local Intelligence

```bash
python -m loopos.cli.app index build --workspace . --data-dir .loopos-demo
python -m loopos.cli.app index symbols --workspace . --data-dir .loopos-demo
python -m loopos.cli.app index imports --workspace . --data-dir .loopos-demo
python -m loopos.cli.app index diff --workspace . --data-dir .loopos-demo
```

Expected result: the local SQLite index reports files, symbols, imports, and current git diff
paths without sending source code to an external provider.

## Release Readiness

```bash
python scripts/ci_report.py --tests-passed 1 --tests-failed 0 --ruff passed --mypy passed
python -m loopos.cli.app release readiness --target founding-preview
python -m loopos.cli.app release readiness --target founding-release --deep --json
```

Expected result: readiness reports separate `source_tree_clean`, `packaged_artifact_clean`,
`test_report_verified`, and `deep_smoke_verified`.

## Deep Smoke

```bash
python -m loopos.release.deep_smoke --json
```

Expected result: local dry-run, policy block, invalid diff gate, SQLite file flow, Fusion trace,
webhook flow, trace replay, review artifact, and registry example checks all pass without
external services.

## Boundaries

Dry-run and replay never invoke side-effecting adapters. Gateway and Fusion demos use local mocks.
Dangerous terminal input is denied. JSON output is the stable automation contract; human formatting
is intended for inspection and screenshots.
