#!/usr/bin/env bash

### Test monorepo integration

cd tests/monorepo || exit 255

npm install

cd contracts || exit 255

if ! crytic-compile .
then echo "Monorepo test failed" && exit 255
else echo "Monorepo test passed" && exit 0
fi
