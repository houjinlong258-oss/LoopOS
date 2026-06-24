# Deployment and Runtime Setup

This page covers three install paths plus the runtime
configuration you need to put LoopOS v0.3 into dev, CI, or a
production-like environment.

## Local development install

Editable install. Source changes in the working tree are
immediately visible to `python -m loopos.cli.app …`.

```bash
git clone https://github.com/houjinlong258-oss/LoopOS.git
cd LoopOS
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev,workbench]"
```

The `dev` extra pulls in pytest, mypy, ruff, and the test
dependencies. The `workbench` extra pulls in `typer` and `rich`,
which give you colored tables and the Typer-rendered `--help`
output.

## Local user install

Use this when you only want to *use* LoopOS, not edit the source.

```bash
python -m pip install "loopos[workbench]"
```

No editable install, no dev deps, no source tree on disk. Once
installed, the `loopos` entry point and the
`python -m loopos.cli.app` form both work.

## CI install

Use this in GitHub Actions / GitLab CI / Jenkins / etc.

```bash
python -m pip install -e ".[dev,workbench]"
```

Then run the same gates the v0.3 CI runs:

```bash
python -m pytest -m "not slow" -q
python -m pytest -m "slow" -q
python -m ruff check .
python -m mypy loopos tests
python scripts/v0_2_readiness_check.py --json
python scripts/v0_3_readiness_check.py --json
python scripts/anti_bloat_check.py --json
python rc_audit_cli_smoke.py
```

The `.github/workflows/ci.yml` file in this repo is the canonical
example. Treat it as the source of truth, not this page, when
adjusting the matrix.

## Provider configuration

LoopOS ships three Provider Runtime transports out of the box:

| Provider              | Needs a key?           | Network?          | Default?          |
| --------------------- | ---------------------- | ----------------- | ----------------- |
| `mock`                | No                     | No                | Yes (--provider mock) |
| `openai-compatible`   | Yes                    | Yes (with --allow-live-provider) | No |
| `ollama`              | No                     | Local only (with --allow-live-provider) | No |

### Mock provider

Works out of the box. No env vars, no keys, no network. Use it
for unit tests, CI, and the Quickstart walkthrough.

### OpenAI-compatible provider

Reads from environment variables:

| Variable            | Purpose                                              |
| ------------------- | ---------------------------------------------------- |
| `OPENAI_API_KEY`    | The API key for the upstream provider.               |
| `OPENAI_BASE_URL`   | The base URL for an OpenAI-compatible endpoint.       |

**Never hard-code keys in source, config, or docs.** Use your
shell's secret manager (e.g. `direnv`, `1Password CLI`, `pass`,
or your CI provider's encrypted secret store). See
[SECURITY.md](../SECURITY.md) for the project's secret-handling
policy.

### Ollama

Run Ollama locally and LoopOS can talk to it through the
`ollama` provider. No keys needed. Set `OLLAMA_HOST` if you run
Ollama on a non-default host/port.

## Safe live provider smoke

LoopOS ships a loopback live-provider HTTP smoke
(`scripts/v0_3_live_provider_smoke_http.py`) that exercises the
governed transport stack end-to-end **without** calling a paid
external provider. It spins up a local HTTP server that mimics
the OpenAI-compatible wire format and runs the live code path
against it.

```bash
python scripts/v0_3_live_provider_smoke_http.py
```

Use this when you want to verify the live-transport code path
without spending money or depending on the public internet.

You can opt into the smoke from the v0.3 readiness proof by
setting the gate env var:

```bash
LOOPOS_LIVE_HTTP_SMOKE=1 python scripts/v0_3_readiness_check.py --json
```

## Running readiness checks

| Command                                          | What it proves                                     |
| ------------------------------------------------ | -------------------------------------------------- |
| `python scripts/v0_2_readiness_check.py --json`  | v0.2 substrate still healthy (regression guard).   |
| `python scripts/v0_3_readiness_check.py --json`  | All 26 v0.3 readiness checks pass.                 |
| `python scripts/anti_bloat_check.py --json`      | No bloat / file-size gates tripped.                |

The `loopos readiness check` command is a thin wrapper over
`scripts/v0_3_readiness_check.py`; both write the same JSON
shape and exit with the same code.

## Updating / upgrading

```bash
git pull
python -m pip install -e ".[dev,workbench]"
```

The `git pull` updates the source; the second `pip install` is
needed only if `pyproject.toml` or the extras changed. If the
upgrade is within the v0.3 line, the v0.3 readiness proof should
still pass.

## Uninstall / cleanup

LoopOS keeps its runtime state under `.loopos/` inside the
working directory by default. To fully clean up:

```bash
# 1. Remove the Python install
pip uninstall loopos

# 2. Remove local runtime state (sessions, fusion plans, etc.)
rm -rf .loopos
```

Do **not** delete `scripts/baselines/v0_1_0_loopos.txt` or
`dist/LoopOS-v0.2.0-source.zip` — they are the frozen v0.1.0 /
v0.2.0 release evidence and are protected by the freeze notice
at the top of `README.md`.

## Troubleshooting

| Symptom                                              | Likely fix                                                              |
| ---------------------------------------------------- | ----------------------------------------------------------------------- |
| `command not found: loopos`                          | Activate the venv (`source .venv/bin/activate` or `.venv\Scripts\Activate.ps1`). |
| `ModuleNotFoundError: rich` / `typer`                | `pip install -e ".[workbench]"`                                          |
| `OPENAI_API_KEY` not set when going live             | Set the env var, or use the mock provider.                              |
| `provider blocked: live_provider_requires_explicit_approval` | You passed live flags without `--allow-live-provider` or without `--confirm`. The check is intentional. |
| `--json` output contains Rich markup                | This should not happen. File an issue with the command and the output.  |
| `pytest -m slow` takes >2 minutes on a loaded box    | The slow suite runs a deterministic deep smoke; `--maxfail=1 -x` to fail fast. |
| Tests flake on Windows path normalization            | Use `os.devnull` for placeholder paths, not `C:\Windows\…`.           |

Still stuck? Open an issue with the output of:

```bash
python -m loopos.cli.app --version
python -m loopos.cli.app readiness check --json
python -m pip freeze | head -50
```
