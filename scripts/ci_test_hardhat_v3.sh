#!/usr/bin/env bash
set -euo pipefail

echo "Testing hardhat (v3) integration of $(realpath "$(which crytic-compile)")"

cd tests/hardhat-v3 || exit 255

npm install

if ! crytic-compile .
then echo "Hardhat monorepo (v3) test failed" && exit 255
else echo "Hardhat monorepo (v3) test passed" && exit 0
fi
