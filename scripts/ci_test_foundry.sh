#!/usr/bin/env bash

# Test foundry integration

# Setup temp environment
DIR=$(mktemp -d)
cd "$DIR" || exit 255

# The foundry init process makes a temporary local git repo and needs certain values to be set
git config --global user.email "ci@trailofbits.com"
git config --global user.name "CI User"

# Install foundry if it's not already present
if [[ -z "$(command -v foundryup)" ]]
then
  curl -L https://foundry.paradigm.xyz | bash
  export PATH=$PATH:/home/runner/.foundry/bin
fi

foundryup
forge init

if ! crytic-compile .
then echo "Foundry test failed" && exit 255
else echo "Foundry test passed" && exit 0
fi
