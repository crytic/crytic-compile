#!/usr/bin/env bash

echo "Testing monorepo integration of $(realpath "$(which crytic-compile)")"

cd tests/monorepo || exit 255

npm install

echo "Testing from the root of a monorepo"
if ! crytic-compile ./contracts
then echo "Monorepo test failed" && exit 255
fi

cd contracts || exit 255

echo "Testing from within a subdir of a monorepo"
if ! crytic-compile .
then echo "Monorepo test failed" && exit 255
fi

echo "Monorepo test passed" && exit 0
