#!/usr/bin/env bash
set -euo pipefail

### Test buidler integration

cd tests/buidler || exit 255

npm install --save-dev @nomiclabs/buidler

if ! crytic-compile .
then
    echo "buidler test failed"
    exit 255
fi
