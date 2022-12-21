#!/usr/bin/env bash

### Test metadata parsing

DIR=$(mktemp -d)

cp tests/metadata_test.py "$DIR"
cd "$DIR" || exit 255

solc-select use 0.5.12 --always-install

python metadata_test.py $GITHUB_ETHERSCAN > metadata_test_output.json

cd - || exit 255
DIFF=$(diff "$DIR/metadata_test_output.json" tests/expected/metadata.json)
if [ "$?" != "0" ] || [ "$DIFF" != "" ]
then  
    echo "metadata test failed"
    echo "$DIFF"
    exit 255
fi