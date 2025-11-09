# Makefile for ebook2audiobook development

.PHONY: help install install-dev test lint format clean run docker-build docker-up docker-down

# Default target
help:
	@echo "ebook2audiobook - Development Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install       - Install production dependencies"
	@echo "  install-dev   - Install development dependencies"
	@echo "  test          - Run tests with coverage"
	@echo "  test-fast     - Run tests without slow tests"
	@echo "  lint          - Run all linters"
	@echo "  format        - Format code with black and isort"
	@echo "  clean         - Clean up temporary files"
	@echo "  run           - Run the application"
	@echo "  docker-build  - Build development Docker container"
	@echo "  docker-up     - Start development Docker container"
	@echo "  docker-down   - Stop development Docker container"
	@echo "  docker-shell  - Open shell in development container"
	@echo "  pre-commit    - Run pre-commit hooks"
	@echo "  security      - Run security checks"

# Installation
install:
	pip install -r requirements.txt
	pip install -e .

install-dev: install
	pip install -r requirements-dev.txt
	pre-commit install

# Testing
test:
	pytest --cov=lib --cov-report=html --cov-report=term-missing

test-fast:
	pytest -m "not slow" --cov=lib

test-unit:
	pytest -m unit

test-integration:
	pytest -m integration

# Linting
lint: lint-flake8 lint-mypy lint-pylint

lint-flake8:
	flake8 .

lint-mypy:
	mypy .

lint-pylint:
	pylint lib app.py

# Formatting
format:
	black .
	isort .

format-check:
	black --check .
	isort --check-only .

# Security
security:
	bandit -r lib
	safety check

# Cleaning
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build dist htmlcov .coverage

# Running
run:
	python app.py

run-headless:
	python app.py --headless --ebook ebooks/test.epub

# Docker
docker-build:
	docker-compose -f docker-compose.dev.yml build

docker-up:
	docker-compose -f docker-compose.dev.yml up -d

docker-down:
	docker-compose -f docker-compose.dev.yml down

docker-shell:
	docker-compose -f docker-compose.dev.yml exec dev zsh

docker-logs:
	docker-compose -f docker-compose.dev.yml logs -f

docker-rebuild:
	docker-compose -f docker-compose.dev.yml build --no-cache

# Pre-commit
pre-commit:
	pre-commit run --all-files

pre-commit-update:
	pre-commit autoupdate

# Documentation
docs:
	@echo "Development documentation available in DEVELOPMENT.md"

# All checks before commit
check: format lint test
	@echo "✅ All checks passed!"
