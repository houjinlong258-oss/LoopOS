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

Preview the next deterministic instruction:

```bash
python -m loopos.cli.app run "inspect this workspace" --dry-run
```

Run the deterministic MVP loop:

```bash
python -m loopos.cli.app run "demo task" --max-steps 3
```

Generate governed memory proposals from a run:

```bash
python -m loopos.cli.app run "demo task" --max-steps 3 --propose-memory --llm-provider mock
python -m loopos.cli.app memory review
python -m loopos.cli.app memory accept PROPOSAL_ID
```

## Inspect State

Runs are stored under `.loopos/` by default.

```bash
python -m loopos.cli.app status RUN_ID
python -m loopos.cli.app history RUN_ID
python -m loopos.cli.app skills
python -m loopos.cli.app memory
python -m loopos.cli.app memory search pytest
python -m loopos.cli.app profile show
python -m loopos.cli.app policy list
python -m loopos.cli.app policy check --scope terminal.execute --input "{\"cmd\":\"rm -rf tmp\"}"
python -m loopos.cli.app config
```

## Verify

```bash
python -m pytest
python -m ruff check .
python -m mypy loopos tests
```
