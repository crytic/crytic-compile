#!/usr/bin/env bash

### Test truffle integration

mkdir /tmp/waffle
cd /tmp/waffle

curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install --lts
nvm use --lts

npm install -g ethereum-waffle
npm install openzeppelin-solidity
mkdir contracts
cd contracts
echo 'pragma solidity ^0.5.1;

import "openzeppelin-solidity/contracts/token/ERC20/ERC20.sol";


// Example class - a mock class using delivering from ERC20
contract BasicTokenMock is ERC20 {
  constructor(address initialAccount, uint256 initialBalance) public {
    super._mint(initialAccount, initialBalance);
  }
}' > token.sol

cd ..

crytic-compile . --compile-remove-metadata --compile-force-framework Waffle

if [ $? -ne 0 ]
then
    echo "Waffle test failed"
    exit -1
fi

