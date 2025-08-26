#!/usr/bin/env bash
set -euo pipefail

### Test etherlime integration

DIR=$(mktemp -d)
cd "$DIR" || exit 255

npm i -g etherlime
etherlime init

if ! crytic-compile . --compile-remove-metadata
then
    echo "Etherlime test failed"
    exit 255
fi

