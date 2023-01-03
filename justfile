
shell:
  nix-shell shell.nix

build:
  nix-build default.nix

install:
  nix-env -e $(nix-env -q | grep "crytic-compile")
  nix-env -i ./result



lint: black pylint darglint mypy

black:
  nix-build nix/black.nix
  ./result/bin/black crytic_compile --config pyproject.toml

pylint:
  nix-build nix/pylint.nix
  ./result/bin/pylint crytic_compile --rcfile pyproject.toml

darglint:
  nix-build nix/darglint.nix
  ./result/bin/darglint crytic_compile

mypy:
  nix-build nix/mypy.nix
  ./result/bin/mypy crytic_compile



test: test-hardhat test-monorepo test-brownie

test-monorepo:
	bash scripts/ci_test_monorepo.sh

test-hardhat:
	bash scripts/ci_test_hardhat.sh

test-brownie:
	bash scripts/ci_test_brownie.sh
