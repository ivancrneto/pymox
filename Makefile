.PHONY: help install test test-cov lint format precommit clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Editable install with dev + lint tooling
	python -m pip install -e ".[dev,lint]"
	pre-commit install

test:  ## Run the test suite
	pytest test

test-cov:  ## Run tests with branch coverage (as CI does)
	pytest --cov=mox --cov-branch --cov-report=term-missing test

lint:  ## Run all linters/formatters in check mode (Ruff + bandit, via pre-commit)
	pre-commit run --all-files

format:  ## Auto-format and sort imports in place
	ruff check --fix mox pymox test tools
	ruff format mox pymox test tools

clean:  ## Remove build/test artifacts
	rm -rf build dist *.egg-info .pytest_cache .coverage coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
