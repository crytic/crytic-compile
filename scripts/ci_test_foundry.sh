#!/usr/bin/env bash

### Test foundry integration


cd /tmp || exit 255

curl -L https://foundry.paradigm.xyz | bash
source ~/.bash_profile
foundryup

forge init

crytic-compile .
if [ $? -ne 0 ]
then
    echo "hardhat test failed"
    exit 255
fi
