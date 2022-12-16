#!/usr/bin/env bash

DIR=$(mktemp -d)

cp tests/contract.sol "$DIR"
cd "$DIR" || exit 255
crytic-compile contract.sol --compile-remove-metadata --export-format truffle

cd - || exit 255
DIFF=$(diff "$DIR/crytic-export/C.json" tests/expected/solc-demo.json)
if [ "$?" != "0" ] || [ "$DIFF" != "" ]
then  
    echo "solc test failed"
    echo "$DIFF"
    exit 255
fi


