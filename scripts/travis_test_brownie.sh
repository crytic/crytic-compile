#!/usr/bin/env bash

pip install eth-brownie
brownie bake token
cd token || exit 255

crytic-compile . --compile-force-framework Brownie

if [ $? -ne 0 ]
then
    echo "Brownie test failed"
    exit 255
fi
