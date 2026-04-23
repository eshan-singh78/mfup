.PHONY: install test lint typecheck format check build smoke clean

install:
	pip install -e ".[dev]"

test:
	pytest -v

cov:
	pytest -v --cov=mfup --cov-report=term-missing

lint:
	ruff check .

format:
	ruff format .

format-check:
	ruff format --check .

typecheck:
	mypy coremfup/mfup

check: lint format-check typecheck test

build:
	pyinstaller --clean --noconfirm mfup.spec

smoke: build
	./dist/mfup --version
	./dist/mfup --help

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
