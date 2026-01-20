#!/usr/bin/env bash
set -euo pipefail

DIR=$(mktemp -d)

cp tests/contract.sol "$DIR"
cd "$DIR" || exit 255
crytic-compile contract.sol --compile-remove-metadata --export-format solc

cd - || exit 255
node tests/process_combined_solc.js "$DIR/crytic-export/combined_solc.json" "$DIR"

DIFF=$(diff "$DIR/crytic-export/combined_solc.json" tests/expected/solc-demo.json)
if [ "$?" != "0" ] || [ "$DIFF" != "" ]
then
    echo "solc test failed"
    echo "$DIFF"
    exit 255
fi
