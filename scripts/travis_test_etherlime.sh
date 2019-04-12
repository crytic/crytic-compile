#!/usr/bin/env bash

### Test truffle integration

mkdir /tmp/etherlime
cd /tmp/etherlime

curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install --lts
nvm use --lts

npm i -g etherlime
etherlime init
crytic-compile . --compile-remove-metadata

if [ $? -ne 0 ]
then
    echo "Etherlime test failed"
    exit -1
fi

