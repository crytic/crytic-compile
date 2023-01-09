#!/usr/bin/env bash

DIR=$(mktemp -d)

cp tests/contract.sol "$DIR"
cd "$DIR" || exit 255

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
