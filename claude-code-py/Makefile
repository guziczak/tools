.PHONY: help install install-dev test test-unit test-integration lint format type-check security clean run

help:  ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

install-dev:  ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

test:  ## Run all tests
	pytest tests/ -v --cov

test-unit:  ## Run unit tests only
	pytest tests/unit/ -v --cov

test-integration:  ## Run integration tests only
	pytest tests/integration/ -v --cov

test-watch:  ## Run tests in watch mode
	pytest-watch tests/ -v

lint:  ## Run all linters
	@echo "Running Black..."
	black --check src tests
	@echo "Running isort..."
	isort --check-only src tests
	@echo "Running flake8..."
	flake8 src tests
	@echo "Running mypy..."
	mypy src --ignore-missing-imports

format:  ## Format code with black and isort
	black src tests
	isort src tests

type-check:  ## Run type checking with mypy
	mypy src --ignore-missing-imports

security:  ## Run security checks
	bandit -r src
	safety check

clean:  ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov coverage.xml
	rm -rf build dist

run:  ## Run the application
	python src/main.py

run-test:  ## Run basic test script
	python test_basic.py

coverage:  ## Generate coverage report
	pytest tests/ --cov --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

coverage-open:  ## Open coverage report in browser
	pytest tests/ --cov --cov-report=html
	@python -m webbrowser htmlcov/index.html

pre-commit:  ## Run pre-commit hooks on all files
	pre-commit run --all-files

docs:  ## Generate documentation
	cd docs && make html

# CI targets
ci-test:  ## Run tests for CI
	pytest tests/ -v --cov --cov-report=xml --cov-report=term

ci-lint:  ## Run linting for CI
	black --check src tests
	isort --check-only src tests
	flake8 src tests
	mypy src --ignore-missing-imports

ci-security:  ## Run security checks for CI
	bandit -r src -f json -o bandit-report.json
	safety check --json || true
