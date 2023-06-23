#!/usr/bin/env bash

### Test foundry integration


cd /tmp || exit 255

mkdir forge_test
cd forge_test || exit 255
forge init --no-commit

crytic-compile .
if [ $? -ne 0 ]
then
    echo "foundry test failed"
    exit 255
fi
