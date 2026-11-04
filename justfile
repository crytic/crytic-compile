
dev:
  nix develop

build:
  nix build .#crytic-compile

install:
  nix-env -e $(nix-env -q | grep "crytic-compile")
  nix-env -i ./result


lint: black darglint mypy pylint

black:
  @echo
  nix develop --command black --version
  nix develop --command black crytic_compile --config pyproject.toml

darglint:
  @echo
  nix develop --command darglint --version
  nix develop --command darglint crytic_compile

mypy:
  @echo
  nix develop --command mypy --version
  nix develop --command mypy crytic_compile

pylint:
  @echo
  nix develop --command pylint --version
  nix develop --command pylint crytic_compile --rcfile pyproject.toml


test: test-hardhat test-monorepo

test-brownie:
	echo "brownie tests not supported yet"

test-buidler:
	echo "buidler tests not supported yet"

test-dapp:
	echo "dapp tests not supported yet"

test-embark:
	echo "embark tests not supported yet"

test-etherlime:
	echo "etherlime tests not supported yet"

test-etherscan:
	echo "etherscan tests not supported yet"

test-foundry:
	echo "foundry tests not supported yet"

test-hardhat:
  @echo
  nix develop --command bash scripts/ci_test_hardhat.sh

test-monorepo:
  @echo
  nix develop --command bash scripts/ci_test_monorepo.sh

test-solc:
	echo "solc tests not supported yet"

test-standard:
	echo "standard tests not supported yet"

test-truffle:
	echo "truffle tests not supported yet"

test-waffle:
	echo "waffle tests not supported yet"

