#!/usr/bin/env bash
set -euo pipefail

# https://github.com/eth-brownie/brownie/pull/1873#issuecomment-2927669459
pip install -U setuptools

pip install eth-brownie
brownie bake token
cd token || exit 255

if ! crytic-compile . --compile-force-framework Brownie
then
    echo "Brownie test failed"
    exit 255
fi
