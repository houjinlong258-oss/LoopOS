.PHONY: test lint typecheck ci

PYTHON ?= python

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy loopos tests

ci: lint typecheck test
