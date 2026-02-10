#!/usr/bin/env bash
set -euo pipefail

# web3 imported by brownie still expects pkg_resources.
# setuptools 82+ removed pkg_resources, so pin below 82.
# https://github.com/eth-brownie/brownie/pull/1873#issuecomment-2927669459
pip install -U "setuptools<82"

pip install eth-brownie
brownie bake token
cd token || exit 255

if ! crytic-compile . --compile-force-framework Brownie
then
    echo "Brownie test failed"
    exit 255
fi
