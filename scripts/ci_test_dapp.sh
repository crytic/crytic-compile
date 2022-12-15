#!/usr/bin/env bash

# Test dapp integration

DIR=$(mktemp -d)
cd "$DIR" || exit 255

# The dapp init process makes a temporary local git repo and needs certain values to be set
git config --global user.email "ci@trailofbits.com"
git config --global user.name "CI User"

which nix-env || exit 255

git clone --recursive https://github.com/dapphub/dapptools "$HOME/.dapp/dapptools"
nix-env -f "$HOME/.dapp/dapptools" -iA dapp seth solc hevm ethsign

dapp init

if ! crytic-compile . --compile-remove-metadata
then echo "dapp test failed" && exit 255
else echo "dapp test passed" && exit 0
fi
