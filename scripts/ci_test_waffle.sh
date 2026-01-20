#!/usr/bin/env bash
set -euo pipefail

### Test waffle integration

DIR=$(mktemp -d)
cd "$DIR" || exit 255

npm install -g ethereum-waffle
npm install openzeppelin-solidity
mkdir contracts
cd contracts || exit 255
echo 'contract Test {
  constructor() public {}
}' > token.sol

cd ..

if ! crytic-compile . --compile-remove-metadata --compile-force-framework Waffle
then
    echo "Waffle test failed"
    exit 255
fi
