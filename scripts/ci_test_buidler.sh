#!/usr/bin/env bash

# Test buidler integration

cd tests/buidler || exit 255

npm install || exit 255

if ! crytic-compile .
then echo "Buidler test failed" && exit 255
else echo "Buidler test passed" && exit 0
fi
