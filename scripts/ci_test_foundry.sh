#!/usr/bin/env bash

### Test foundry integration


cd /tmp || exit 255

mkdir forge_test
cd forge_test || exit 255
forge init --no-commit

crytic-compile .
if [ $? -ne 0 ]
then
    echo "foundry test 1 failed"
    exit 255
fi

mkdir /tmp/forge_test/test_2
rsync -a --exclude='test_2' ./ /tmp/forge_test/test_2/
crytic-compile ./test_2
if [ $? -ne 0 ]
then
    echo "foundry test 2 failed"
    exit 255
fi