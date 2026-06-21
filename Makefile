.PHONY: test test-unit test-integration test-acceptance test-fast test-all lint type typecheck check ci

PYTHON ?= python

test: test-all

test-unit:
	$(PYTHON) -m pytest -q -m "unit"

test-integration:
	$(PYTHON) -m pytest -q -m "integration"

test-acceptance:
	$(PYTHON) -m pytest -q -m "acceptance" tests/acceptance_founding

test-fast:
	$(PYTHON) -m pytest -q -m "not slow"

test-all:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

type typecheck:
	$(PYTHON) -m mypy loopos tests

check: test-fast lint type

ci: check test-acceptance
