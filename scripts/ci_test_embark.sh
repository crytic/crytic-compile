#!/usr/bin/env bash

### Test embark integration

cd /tmp || exit 255

curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install 10.17.0
nvm use 10.17.0

npm install -g embark@4.2.0
embark demo
cd /tmp/embark_demo || exit 255
npm install
crytic-compile . --embark-overwrite-config --compile-remove-metadata

if [ $? -ne 0 ]
then
    echo "Embark test failed"
    exit 255
fi

