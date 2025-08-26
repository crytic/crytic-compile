#!/usr/bin/env bash
set -euo pipefail

pip install eth-brownie
brownie bake token
cd token || exit 255

if ! crytic-compile . --compile-force-framework Brownie
then
    echo "Brownie test failed"
    exit 255
fi
