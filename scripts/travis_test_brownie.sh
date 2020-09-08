#!/usr/bin/env bash

pip install eth-brownie
brownie bake token
cd token || exit -1

crytic-compile . --compile-force-framework Brownie

if [ $? -ne 0 ]
then
    echo "Brownie test failed"
    exit -1
fi
