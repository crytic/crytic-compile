#!/usr/bin/env bash

DIR=$(mktemp -d)

cp tests/contract_with_toplevel.sol "$DIR"
cp tests/toplevel.sol "$DIR"
cd "$DIR" || exit 255

solc-select use 0.8.0 --always-install

crytic-compile contract_with_toplevel.sol --export-format archive

if [ $? -ne 0 ]
then
    echo "Standard test failed"
    exit 255
fi

crytic-compile crytic-export/contract_with_toplevel.sol_export_archive.json

if [ $? -ne 0 ]
then
    echo "Standard test failed"
    exit 255
fi


crytic-compile contract_with_toplevel.sol --export-zip test.zip

if [ $? -ne 0 ]
then
    echo "Standard test failed"
    exit 255
fi

crytic-compile test.zip

if [ $? -ne 0 ]
then
    echo "Standard test failed"
    exit 255
fi
