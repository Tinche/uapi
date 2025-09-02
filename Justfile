test *args='tests -x --ff --mypy-only-local-stub':
	pdm run pytest {{args}}

lint:
	pdm run mypy src/ tests/ && pdm run ruff src/ tests/ && pdm run black --check -q src/ tests/
