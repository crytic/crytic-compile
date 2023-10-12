#!/usr/bin/env bash

### Test vyper integration

pip install vyper

echo "Testing vyper integration of $(realpath "$(which crytic-compile)")"

cd tests/vyper || exit 255

if ! crytic-compile auction.vy --export-formats standard
then echo "vyper test failed" && exit 255
else echo "vyper test passed" && exit 0
fi
