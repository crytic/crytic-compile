#!/usr/bin/env bash

# Install eth-brownie if it's not already present
if [[ -z "$(command -v brownie)" ]]
then pip install eth-brownie
fi

brownie bake token

cd token || exit 255

if ! crytic-compile . --compile-force-framework Brownie
then echo "Brownie test failed" && exit 255
else echo "Brownie test passed" && exit 0
fi
