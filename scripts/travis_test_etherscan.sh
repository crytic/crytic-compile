#!/usr/bin/env bash

### Test etherscan integration

mkdir /tmp/etherscan
cd /tmp/etherscan

docker pull trailofbits/solc-select
sudo rm /usr/bin/solc
docker run --read-only -i --rm --entrypoint='/bin/sh' trailofbits/solc-select:latest -c 'cat /usr/bin/install.sh' | bash

crytic-compile 0x7F37f78cBD74481E593F9C737776F7113d76B315 --compile-remove-metadata

if [ $? -ne 0 ]
then
    echo "Etherscan test failed"
    exit -1
fi

crytic-compile rinkeby:0xFe05820C5A92D9bc906D4A46F662dbeba794d3b7 --compile-remove-metadata

if [ $? -ne 0 ]
then
    echo "Etherscan test failed"
    exit -1
fi

