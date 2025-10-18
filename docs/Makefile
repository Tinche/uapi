# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= uv run --group docs sphinx-build -M
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	$(SPHINXBUILD) $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

apidoc:
	uv run --group docs sphinx-apidoc -o . ../src/uapi -f

## htmllive       to rebuild and reload HTML files in your browser
.PHONY: htmllive
htmllive: SPHINXBUILD = uv run --group docs sphinx-autobuild -b
htmllive: SPHINXERRORHANDLING = --re-ignore="/\.idea/|/venv/|/topic/"
htmllive: html
