python := ""
covcleanup := "true"

sync version="":
    uv sync {{ if python != '' { '-p ' + python } else if version != '' { '-p ' + version } else  { '' } }} --all-groups --all-extras

test *args='tests -x --ff --mypy-only-local-stub -n auto':
	uv run pytest {{args}}

lint: sync
	uv run mypy src/ tests/ && uv run ruff check src/ tests/ && uv run black --check src/ tests/

cov *args="-x --ff --mypy-only-local-stub -n auto tests":
    uv run {{ if python != '' { '-p ' + python } else { '' } }} --all-extras --group frameworks --group test --group lint coverage run -m pytest {{args}}
    {{ if covcleanup == "true" { "uv run coverage combine" } else { "" } }}
    {{ if covcleanup == "true" { "uv run coverage report" } else { "" } }}
    {{ if covcleanup == "true" { "@rm .coverage*" } else { "" } }}

covall:
    just python=python3.11 covcleanup=false cov
    just python=python3.12 covcleanup=false cov
    just python=python3.13 covcleanup=false cov
    just python=python3.14 covcleanup=false cov
    uv run coverage combine
    uv run coverage report
    @rm .coverage*

docs output_dir="_build": ## generate Sphinx HTML documentation, including API docs
	make -C docs -e BUILDDIR={{output_dir}} clean
	make -C docs -e BUILDDIR={{output_dir}} doctest
	make -C docs -e BUILDDIR={{output_dir}} html
