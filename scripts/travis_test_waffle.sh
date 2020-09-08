#!/usr/bin/env bash

### Test truffle integration

mkdir /tmp/waffle
cd /tmp/waffle || exit 255

curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install --lts
nvm use --lts

npm install -g ethereum-waffle
npm install openzeppelin-solidity
mkdir contracts
cd contracts
echo 'contract Test {
  constructor() public {}
}' > token.sol

cd ..

crytic-compile . --compile-remove-metadata --compile-force-framework Waffle

if [ $? -ne 0 ]
then
    echo "Waffle test failed"
    exit 255
fi

