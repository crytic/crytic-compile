#!/usr/bin/env bash
set -euo pipefail

DIR=$(mktemp -d)

cp tests/contract_with_toplevel.sol "$DIR"
cp tests/toplevel.sol "$DIR"
cd "$DIR" || exit 255

solc-select use 0.8.0 --always-install

if ! crytic-compile contract_with_toplevel.sol --export-format archive
then
    echo "Standard test failed"
    exit 255
fi

if ! crytic-compile crytic-export/contract_with_toplevel.sol_export_archive.json
then
    echo "Standard test failed"
    exit 255
fi

if ! crytic-compile contract_with_toplevel.sol --export-zip test.zip
then
    echo "Standard test failed"
    exit 255
fi

if ! crytic-compile test.zip
then
    echo "Standard test failed"
    exit 255
fi
