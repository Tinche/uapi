.PHONY: test lint

test:
	pdm run pytest tests -x --ff

lint:
	pdm run mypy src/ tests/ && pdm run flake8 src/ tests/ && pdm run black --check -q src/ tests/ && pdm run isort -cq src/ tests/
