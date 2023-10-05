#!/usr/bin/env bash

DIR=$(mktemp -d)

cp -r tests/hardhat-multi-file "$DIR"
cd "$DIR/hardhat-multi-file" || exit 255
npm install
crytic-compile --compile-remove-metadata --export-formats solc,truffle .

cd - || exit 255
node tests/process_combined_solc.js "$DIR/hardhat-multi-file/crytic-export/combined_solc.json" "$DIR"
DIFF=$(diff -r "$DIR/hardhat-multi-file/crytic-export" tests/expected/hardhat-multi-file)
if [ "$?" != "0" ] || [ "$DIFF" != "" ]
then  
    echo "hardhat-multi-file test failed"
    echo "$DIFF"
    exit 255
fi
