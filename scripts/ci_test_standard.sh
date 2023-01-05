#!/usr/bin/env bash

DIR=$(mktemp -d)

cp tests/contract.sol "$DIR"
cd "$DIR" || exit 255

crytic-compile contract.sol --export-format archive

if [ $? -ne 0 ]
then
    echo "Standard test failed"
    exit 255
fi

crytic-compile crytic-export/contract.sol_export_archive.json

if [ $? -ne 0 ]
then
    echo "Standard test failed"
    exit 255
fi


crytic-compile contract.sol --export-zip test.zip

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
