#!/usr/bin/env bash

cp tests/contract.sol /tmp
cd /tmp || exit -1
crytic-compile contract.sol --compile-remove-metadata

cd -
DIFF=$(diff /tmp/crytic-export/contracts.json tests/expected/solc-demo.json)
if [ "$DIFF" != "" ]
then  
    echo "solc test failed"
    echo $DIFF
    exit -1
fi


