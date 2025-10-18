python := ""

sync version="":
    uv sync {{ if python != '' { '-p ' + python } else if version != '' { '-p ' + version } else  { '' } }} --all-groups --all-extras

test *args='tests -x --ff --mypy-only-local-stub -n auto':
	uv run pytest {{args}}

lint: sync
	uv run mypy src/ tests/ && uv run ruff check src/ tests/ && uv run black --check src/ tests/
