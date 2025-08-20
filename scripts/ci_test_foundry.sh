#!/usr/bin/env bash
### Test foundry integration
set -Eeuxo pipefail


## test 1 - same folder

cd /tmp || exit 255
mkdir forge_test
cd forge_test || exit 255
forge init

crytic-compile .
if [ $? -ne 0 ]
then
    echo "foundry test 1 failed"
    exit 255
fi


## test 2 - same folder, different out dir

cd /tmp || exit 255
mkdir forge_test2
cd forge_test2 || exit 255
forge init

sed -i 's/^out\s*=.*$/out = "foobar"/' foundry.toml

crytic-compile .
if [ $? -ne 0 ]
then
    echo "foundry test 2 failed"
    exit 255
fi

## test 3 - different folder

cd /tmp || exit 255
mkdir forge_test3
cd forge_test3 || exit 255
forge init

cd /tmp || exit 255

crytic-compile ./forge_test3
if [ $? -ne 0 ]
then
    echo "foundry test 3 failed"
    exit 255
fi
