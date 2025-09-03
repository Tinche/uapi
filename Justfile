test *args='tests -x --ff --mypy-only-local-stub -n auto':
	pdm run pytest {{args}}

lint:
	pdm run mypy src/ tests/ && pdm run ruff check src/ tests/ && pdm run black --check src/ tests/
