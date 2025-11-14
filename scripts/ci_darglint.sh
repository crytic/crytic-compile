#!/usr/bin/env bash
set -euo pipefail

pip install darglint

if ! darglint .
then
    echo "Darglint failed. Please fix the above issues"
    exit 255
fi
