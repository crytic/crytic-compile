#!/usr/bin/env bash

### Test etherscan integration

DIR=$(mktemp -d)
cd "$DIR" || exit 255

solc-select use 0.4.25 --always-install

delay_no_key () {
    # Perform a small sleep when API key is not available (e.g. on PR CI from external contributor)
    if [ "$GITHUB_ETHERSCAN" = "" ]; then
        sleep 5s
    fi
}

echo "::group::Etherscan mainnet"
crytic-compile 0x7F37f78cBD74481E593F9C737776F7113d76B315 --compile-remove-metadata --etherscan-apikey "$GITHUB_ETHERSCAN"

if [ $? -ne 0 ]
then
    echo "Etherscan mainnet test failed"
    exit 255
fi
echo "::endgroup::"

delay_no_key

echo "::group::Etherscan rinkeby"
crytic-compile rinkeby:0xFe05820C5A92D9bc906D4A46F662dbeba794d3b7 --compile-remove-metadata --etherscan-apikey "$GITHUB_ETHERSCAN"

if [ $? -ne 0 ]
then
    echo "Etherscan rinkeby test failed"
    exit 255
fi
echo "::endgroup::"

delay_no_key

# From crytic/slither#1154
echo "::group::Etherscan #3"
crytic-compile 0xcfc1E0968CA08aEe88CbF664D4A1f8B881d90f37 --compile-remove-metadata --etherscan-apikey "$GITHUB_ETHERSCAN"

if [ $? -ne 0 ]
then
    echo "Etherscan #3 test failed"
    exit 255
fi
echo "::endgroup::"
