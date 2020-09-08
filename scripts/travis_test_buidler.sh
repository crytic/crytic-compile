#!/usr/bin/env bash

### Test dapp integration

cd tests/buidler || exit 255


curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install 10.17.0
nvm use 10.17.0

npm install --save-dev @nomiclabs/buidler

crytic-compile .
if [ $? -ne 0 ]
then
    echo "buidler test failed"
    exit 255
fi
