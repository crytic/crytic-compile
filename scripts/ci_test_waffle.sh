#!/usr/bin/env bash

# Test waffle integration

DIR=$(mktemp -d)
cd "$DIR" || exit 255

# Install waffle if it's not already present
if [[ -z "$(command -v waffle)" ]]
then npm install -g ethereum-waffle
fi

npm install openzeppelin-solidity

mkdir contracts

echo 'contract Test {
  constructor() public {}
}' > contracts/token.sol

if ! crytic-compile . --compile-remove-metadata --compile-force-framework Waffle
then echo "Waffle test failed" && exit 255
else echo "Waffle test passed" && exit 0
fi
