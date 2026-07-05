ifneq (,$(wildcard .env))
include .env
export
endif

VENV := .venv
PYTHON := $(VENV)/bin/python

.PHONY: help install up down run load-data smoke test lint fmt audit docs docs-serve clean

help: ## Show this help
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Create venv and install with dev dependencies
	python3.12 -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

up: ## Start PostgreSQL via Docker Compose
	docker compose up -d --wait

down: ## Stop PostgreSQL
	docker compose down

run: ## Run the MCP server on stdio
	$(PYTHON) -m mcp_data_gateway.server

load-data: ## Load the Titanic demo dataset
	$(PYTHON) scripts/load_titanic.py

smoke: ## End-to-end smoke test against the running stack
	$(PYTHON) scripts/smoke_test.py

test: ## Run the test suite
	$(PYTHON) -m pytest

lint: ## Ruff lint and format check
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

fmt: ## Auto-format
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

audit: ## Security static analysis and dependency audit
	$(PYTHON) -m bandit -c pyproject.toml -r src scripts
	$(PYTHON) -m pip_audit

docs: ## Build the documentation site into site/
	$(PYTHON) -m mkdocs build --strict

docs-serve: ## Preview the documentation site with live reload
	$(PYTHON) -m mkdocs serve

clean: ## Remove venv and caches
	rm -rf $(VENV) .pytest_cache .ruff_cache dist build site
