#!/usr/bin/env bash

### Test hardhat integration

cd tests/hardhat || exit 255

npm install

crytic-compile .
if [ $? -ne 0 ]
then
    echo "hardhat test failed"
    exit 255
fi
