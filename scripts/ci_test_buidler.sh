#!/usr/bin/env bash

### Test buidler integration

cd tests/buidler || exit 255

npm install --save-dev @nomiclabs/buidler

crytic-compile .
if [ $? -ne 0 ]
then
    echo "buidler test failed"
    exit 255
fi
