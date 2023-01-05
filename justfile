
dev:
  nix-shell shell.nix

build:
  nix-build default.nix

install:
  nix-env -e $(nix-env -q | grep "crytic-compile")
  nix-env -i ./result


lint: black darglint mypy pylint

black:
  @echo -e "\nBuilding black.."
  nix-build nix/black.nix > /dev/null
  @echo "Running black.."
  ./result/bin/black --version
  ./result/bin/black crytic_compile --config pyproject.toml

darglint:
  @echo -e "\nBuilding darglint.."
  nix-build nix/darglint.nix > /dev/null
  @echo "Running darglint.."
  ./result/bin/darglint --version
  ./result/bin/darglint crytic_compile

mypy:
  @echo -e "\nBuilding mypy.."
  nix-build nix/mypy.nix > /dev/null
  @echo "Running mypy.."
  ./result/bin/mypy --version
  ./result/bin/mypy crytic_compile

pylint:
  @echo -e "\nBuilding pylint.."
  nix-build nix/pylint.nix > /dev/null
  @echo "Running pylint.."
  ./result/bin/pylint --version
  ./result/bin/pylint crytic_compile --rcfile pyproject.toml


test: test-hardhat test-monorepo test-brownie

test-monorepo:
	bash scripts/ci_test_monorepo.sh

test-hardhat:
	bash scripts/ci_test_hardhat.sh

test-brownie:
	bash scripts/ci_test_brownie.sh
