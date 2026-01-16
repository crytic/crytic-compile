# Contributing to crytic-compile
First, thanks for your interest in contributing to crytic-compile! We welcome and appreciate all contributions, including bug reports, feature suggestions, tutorials/blog posts, and code improvements.

If you're unsure where to start, we recommend our [`good first issue`](https://github.com/crytic/crytic-compile/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) and [`help wanted`](https://github.com/crytic/crytic-compile/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) issue labels.

## Bug reports and feature suggestions
Bug reports and feature suggestions can be submitted to our issue tracker. For bug reports, attaching the contract that caused the bug will help us in debugging and resolving the issue quickly. If you find a security vulnerability, do not open an issue; email opensource@trailofbits.com instead.

## Questions
Questions can be submitted to the issue tracker, but you may get a faster response if you ask in our [chat room](https://slack.empirehacking.nyc/) (in the #ethereum channel).

## Code
crytic-compile uses the pull request contribution model. Please make an account on Github, fork this repo, and submit code contributions via pull request. For more documentation, look [here](https://guides.github.com/activities/forking/).

Some pull request guidelines:

- Work from the [`master`](https://github.com/crytic/crytic-compile/tree/master) branch.
- Minimize irrelevant changes (formatting, whitespace, etc) to code that would otherwise not be touched by this patch. Save formatting or style corrections for a separate pull request that does not make any semantic changes.
- When possible, large changes should be split up into smaller focused pull requests.
- Fill out the pull request description with a summary of what your patch does, key changes that have been made, and any further points of discussion, if applicable.
- Title your pull request with a brief description of what it's changing. "Fixes #123" is a good comment to add to the description, but makes for an unclear title on its own.
- We use the [Google style guide](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings) for documentation.
- If there are specific operations whose purpose would not be clear to a naive user, documentation should alleviate that.
- Add type hints to function parameters, return variables, class variables, lists and sets. If possible add type hints to dictionaries.

## Linters

Several linters and security checkers are run on the PRs.

To run them locally:

- `ruff check crytic_compile/`
- `ruff format --check .`
- `ty check crytic_compile/`

Tool versions are managed in `pyproject.toml`.

### Pre-commit Hooks

We use [prek](https://github.com/j178/prek), a fast Rust-based pre-commit runner:

```bash
prek install               # One-time setup (done by make dev)
prek run --all-files       # Run manually on all files
prek auto-update --cooldown-days 7  # Update hook versions
```

## Development Environment

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup development environment
make dev  # Installs dependencies and pre-commit hooks
```

For alternative installation methods, see our [wiki](https://github.com/crytic/crytic-compile/wiki/Developer-installation).
