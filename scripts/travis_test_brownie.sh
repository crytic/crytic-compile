#!/usr/bin/env bash

pip install eth-brownie
brownie bake token
cd token

crytic-compile . 

if [ $? -ne 0 ]
then
    echo "Brownie test failed"
    exit -1
fi
