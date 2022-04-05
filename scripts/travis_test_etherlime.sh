#!/usr/bin/env bash

### Test etherlime integration

DIR=$(mktemp -d)
cd "$DIR" || exit 255

npm i -g etherlime
etherlime init
crytic-compile . --compile-remove-metadata

if [ $? -ne 0 ]
then
    echo "Etherlime test failed"
    exit 255
fi

