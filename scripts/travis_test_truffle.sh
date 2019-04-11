#!/usr/bin/env bash

### Test truffle integration

cd /tmp

curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install --lts
nvm use --lts

npm install -g truffle
truffle unbox metacoin
crytic-compile . --compilation-remove-metadata

cd -

DIFF=$(diff /tmp/crytic-export/contracts.json tests/expected/truffle-metacoin.json)
if [ "$DIFF" != "" ]
then  
    echo "Truffle test failed"
    echo $DIFF
    exit -1
fi

