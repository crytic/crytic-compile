#!/usr/bin/env bash

pip install darlint

darglint .

if [ $? -ne 0 ]
then
    echo "Darglint failed. Please fix the above issues"
    exit 255
fi
