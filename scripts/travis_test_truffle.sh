#!/usr/bin/env bash

### Test truffle integration

mkdir test_truffle
cd test_truffle

curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install --lts
nvm use --lts

npm install -g truffle
truffle unbox metacoin
crytic-compile .

DIFF=$(diff crytic-export/contracts.json ../tests/expected/truffle-metacoin.json)
if [ "$DIFF" != "" ]
then  
    echo "Truffle test failed"
    exit -1
fi

