#!/usr/bin/env bash

### Test embark integration

mkdir test_embark
cd test_embark

curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install --lts
nvm use --lts
npm --version

npm install -g embark
embark demo
cd embark_demo
npm install
crytic-compile . --embark-overwrite-config

DIFF=$(diff crytic-export/contracts.json ../../tests/expected/embark-demo.json)
if [ "$DIFF" != "" ]
then  
    echo "Embark test failed"
    exit -1
fi


