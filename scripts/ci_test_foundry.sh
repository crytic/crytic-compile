#!/usr/bin/env bash

### Test foundry integration


cd /tmp || exit 255

curl -L https://foundry.paradigm.xyz | bash
export PATH=$PATH:/home/runner/.foundry/bin
foundryup

mkdir forge_test
cd forge_test || exit 255
forge init

crytic-compile .
if [ $? -ne 0 ]
then
    echo "foundry test failed"
    exit 255
fi
