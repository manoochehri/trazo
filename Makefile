.PHONY: setup test lint fmt scan docs changelog release
setup:            ## install deps and git hooks
	uv sync
	uv run pre-commit install
test:
	uv run pytest
lint:
	uv run ruff check . && uv run ruff format --check .
fmt:
	uv run ruff check --fix . && uv run ruff format .
scan:             ## scan full git history for secrets
	scripts/scan.sh
docs:             ## preview the docs site locally
	uv run --group docs mkdocs serve
changelog:        ## print a draft entry from closed issues in the release milestone
	scripts/changelog.sh $(if $(VERSION),--version $(VERSION),)
release:          ## cut a release: validate, then tag and push vX.Y.Z
	scripts/release.sh
