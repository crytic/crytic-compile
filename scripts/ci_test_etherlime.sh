#!/usr/bin/env bash

# Test etherlime integration

DIR=$(mktemp -d)
cd "$DIR" || exit 255

# Install etherlime if it's not already present
if [[ -z "$(command -v etherlime)" ]]
then npm i -g etherlime
fi

etherlime init

if ! crytic-compile . --compile-remove-metadata
then echo "Etherlime test failed" && exit 255
else echo "Etherlime test passed" && exit 0
fi
