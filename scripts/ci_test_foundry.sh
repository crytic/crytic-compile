#!/usr/bin/env bash

### Test foundry integration


cd /tmp || exit 255

curl -L https://foundry.paradigm.xyz | bash
export PATH=$PATH:/home/runner/.foundry/bin
foundryup

# The foundry init process makes a temporary local git repo and needs certain values to be set
git config --global user.email "ci@trailofbits.com"
git config --global user.name "CI User"

mkdir forge_test
cd forge_test || exit 255
forge init

# base test: just a "forge init" project

crytic-compile .
if [ $? -ne 0 ]
then
    echo "foundry base test failed"
    exit 255
fi


# extra files test: "forge init" but with extra_output_files enabled (issue #296)
forge clean
echo >> foundry.toml # missing newline at the end of template
echo 'extra_output_files = ["metadata", "abi"]' >> foundry.toml

crytic-compile .
if [ $? -ne 0 ]
then
    echo "foundry extra files test failed"
    exit 255
fi