#!/usr/bin/env bash

### Test etherscan integration

mkdir /tmp/etherscan
cd /tmp/etherscan  || exit 255

solc-select use 0.4.25 --always-install

crytic-compile 0x7F37f78cBD74481E593F9C737776F7113d76B315 --compile-remove-metadata --etherscan-apikey "$GITHUB_ETHERSCAN"

if [ $? -ne 0 ]
then
    echo "Etherscan test failed"
    exit 255
fi

crytic-compile rinkeby:0xFe05820C5A92D9bc906D4A46F662dbeba794d3b7 --compile-remove-metadata --etherscan-apikey "$GITHUB_ETHERSCAN"

if [ $? -ne 0 ]
then
    echo "Etherscan test failed"
    exit 255
fi

