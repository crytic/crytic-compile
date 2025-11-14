#!/usr/bin/env bash
set -euo pipefail

### Test truffle integration

DIR=$(mktemp -d)
cd "$DIR" || exit 255

npm install -g truffle
truffle unbox metacoin

if ! crytic-compile . --compile-remove-metadata
then
    echo "Truffle test failed"
    exit 255
fi
# TODO: for some reason truffle output is not deterministic
# The assigned id changes
#cd -
#
#DIFF=$(diff "$DIR/crytic-export/contracts.json" tests/expected/truffle-metacoin.json)
#if [ "$DIFF" != "" ]
#then  
#    echo "Truffle test failed"
#    echo $DIFF
#    exit 255
#fi

