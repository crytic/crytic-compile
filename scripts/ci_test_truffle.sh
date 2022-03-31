#!/usr/bin/env bash

### Test truffle integration

mkdir /tmp/truffle
cd /tmp/truffle || exit 255

curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install --lts
nvm use --lts

npm install -g truffle
truffle unbox metacoin
crytic-compile . --compile-remove-metadata

if [ $? -ne 0 ]
then
    echo "Truffle test failed"
    exit 255
fi
# TODO: for some reason truffle output is not deterministc
# The assigned id changes
#cd -
#
#DIFF=$(diff /tmp/truffle/crytic-export/contracts.json tests/expected/truffle-metacoin.json)
#if [ "$DIFF" != "" ]
#then  
#    echo "Truffle test failed"
#    echo $DIFF
#    exit 255
#fi

