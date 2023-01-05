#!/usr/bin/env bash

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

crytic-compile . --compile-remove-metadata --compile-force-framework Waffle

if [ $? -ne 0 ]
then
    echo "Waffle test failed"
    exit 255
fi

