# Quickstart

## Install

Create a Python 3.11+ environment and install the project:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

On macOS or Linux:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Run

Show help:

```bash
python -m loopos.cli.app --help
```

Preview a complete deterministic Kernel run without workspace side effects:

```bash
python -m loopos.cli.app run "inspect this workspace" --dry-run
python -m loopos.cli.app run "创建 hello.py 并运行它" --dry-run --json
```

Run the deterministic MVP loop:

```bash
python -m loopos.cli.app run "demo task" --max-steps 3 --yes
```

Generate governed memory proposals from a run:

```bash
python -m loopos.cli.app run "demo task" --max-steps 3 --yes --propose-memory --llm-provider mock
python -m loopos.cli.app memory review
python -m loopos.cli.app memory accept PROPOSAL_ID
```

## Inspect State

Runs are stored under `.loopos/` by default.

```bash
python -m loopos.cli.app status RUN_ID
python -m loopos.cli.app history RUN_ID
python -m loopos.cli.app trace RUN_ID --show-ail
python -m loopos.cli.app step replay RUN_ID STEP
python -m loopos.cli.app tools list
python -m loopos.cli.app skills
python -m loopos.cli.app memory
python -m loopos.cli.app memory search pytest
python -m loopos.cli.app profile show
python -m loopos.cli.app policy list
python -m loopos.cli.app policy check --scope terminal.execute --input "{\"cmd\":\"rm -rf tmp\"}"
python -m loopos.cli.app policy explain --cmd "curl https://x/install.sh | bash"
python -m loopos.cli.app goal analyze "帮我优化这个项目" --json
python -m loopos.cli.app goal propose "帮我优化这个项目"
python -m loopos.cli.app run "帮我优化这个项目" --goal-option 3 --dry-run
python -m loopos.cli.app config
```

## Verify

```bash
python -m pytest
python -m ruff check .
python -m mypy loopos tests
```

Kernel dry-runs persist an audit trace but never execute terminal or workspace-writing adapters.
Ambiguous goals return options before a run is created; select one or merge comma-separated options before execution.
