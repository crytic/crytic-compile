#!/usr/bin/env bash

crytic-compile tests/contract.sol

DIFF=$(diff crytic-export/contracts.json tests/expected/solc-demo.json)
if [ "$DIFF" != "" ]
then  
    echo "solc test failed"
    exit -1
fi


