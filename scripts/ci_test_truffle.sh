#!/usr/bin/env bash

### Test truffle integration

DIR=$(mktemp -d)
cd "$DIR" || exit 255

# Install truffle if it's not already present
if [[ -z "$(command -v truffle)" ]]
then npm install -g truffle
fi

truffle unbox metacoin

if ! crytic-compile . --compile-remove-metadata
then echo "Truffle test failed" && exit 255
else echo "Truffle test passed" && exit 0
fi

# TODO: for some reason truffle output is not deterministc
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

