# Contributing to crytic-compile
First, thanks for your interest in contributing to crytic-compile! We welcome and appreciate all contributions, including bug reports, feature suggestions, tutorials/blog posts, and code improvements.

If you're unsure where to start, we recommend our [`good first issue`](https://github.com/crytic/crytic-compile/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) and [`help wanted`](https://github.com/crytic/crytic-compile/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) issue labels.

## Bug reports and feature suggestions
Bug reports and feature suggestions can be submitted to our issue tracker. For bug reports, attaching the contract that caused the bug will help us in debugging and resolving the issue quickly. If you find a security vulnerability, do not open an issue; email opensource@trailofbits.com instead.

## Questions
Questions can be submitted to the issue tracker, but you may get a faster response if you ask in our [chat room](https://empireslacking.herokuapp.com/) (in the #ethereum channel).

## Code
crytic-compile uses the pull request contribution model. Please make an account on Github, fork this repo, and submit code contributions via pull request. For more documentation, look [here](https://guides.github.com/activities/forking/).

Some pull request guidelines:

- Work from the [`dev`](https://github.com/crytic/crytic-compile/tree/dev) branch. We perform extensive tests prior to merging anything to `master`, working from `dev` will allow us to merge your work faster.
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

- `pylint crytic_compile --rcfile pyproject.toml`
- `black crytic_compile --config pyproject.toml`
- `mypy crytic_compile --config mypy.ini`
- `darglint crytic_compile`


We use pylint `2.13.4`, black `22.3.0`, mypy `0.942` and darglint `1.8.0`.

## Development Environment
Instructions for installing a development version of crytic-compile can be found in our [wiki](https://github.com/crytic/crytic-compile/wiki/Developer-installation).
