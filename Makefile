.PHONY: test

test:
	pytest tests -x --ff

lint:
	flake8 src/ tests/ && black --check -q src/ tests/ && isort -cq src/ tests/ && mypy src/ tests/
