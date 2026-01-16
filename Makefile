.PHONY: dev lint reformat test clean docs

PY_MODULE := crytic_compile
TEST_MODULE := tests

dev:
	uv sync --extra dev
	prek install

lint:
	uv run ruff check $(PY_MODULE) $(TEST_MODULE)
	uv run ruff format --check .
	uv run ty check $(PY_MODULE)

reformat:
	uv run ruff check --fix $(PY_MODULE) $(TEST_MODULE)
	uv run ruff format .

test:
	uv run pytest --cov=$(PY_MODULE) $(TEST_MODULE)

clean:
	rm -rf build dist *.egg-info .pytest_cache .coverage htmlcov

docs:
	uv run pdoc --html --output-dir docs $(PY_MODULE)
