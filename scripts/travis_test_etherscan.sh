#!/usr/bin/env bash

### Test etherscan integration

mkdir /tmp/etherscan
cd /tmp/etherscan

wget -O solc-0.4.25 https://github.com/ethereum/solidity/releases/download/v0.4.25/solc-static-linux
chmod +x solc-0.4.25

crytic-compile 0x7F37f78cBD74481E593F9C737776F7113d76B315 --compile-remove-metadata --solc "./solc-0.4.25" --etherscan-apikey $GITHUB_ETHERSCAN

if [ $? -ne 0 ]
then
    echo "Etherscan test failed"
    exit -1
fi

crytic-compile rinkeby:0xFe05820C5A92D9bc906D4A46F662dbeba794d3b7 --compile-remove-metadata --solc "./solc-0.4.25"  --etherscan-apikey $GITHUB_ETHERSCAN

if [ $? -ne 0 ]
then
    echo "Etherscan test failed"
    exit -1
fi

