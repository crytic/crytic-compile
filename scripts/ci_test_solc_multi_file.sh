#!/usr/bin/env bash

DIR=$(mktemp -d)

cp -r tests/solc-multi-file "$DIR"
cd "$DIR/solc-multi-file" || exit 255
crytic-compile --compile-remove-metadata --export-formats solc,truffle A.sol

cd - || exit 255
node tests/process_combined_solc.js "$DIR/solc-multi-file/crytic-export/combined_solc.json" "$DIR"
DIFF=$(diff -r "$DIR/solc-multi-file/crytic-export" tests/expected/solc-multi-file)
if [ "$?" != "0" ] || [ "$DIFF" != "" ]
then  
    echo "solc-multi-file test failed"
    echo "$DIFF"
    exit 255
fi
