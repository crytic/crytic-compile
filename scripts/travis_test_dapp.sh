#!/usr/bin/env bash

### Test dapp integration

mkdir /tmp/dapp
cd /tmp/dapp || exit 255
# The dapp init process makes a temporary local git repo and needs certain values to be set
git config --global user.email "ci@trailofbits.com"
git config --global user.name "CI User"


# curl https://nixos.org/nix/install | sh
# . "$HOME/.nix-profile/etc/profile.d/nix.sh"

curl https://dapp.tools/install | sh

dapp init

crytic-compile . --compile-remove-metadata
if [ $? -ne 0 ]
then
    echo "dapp test failed"
    exit 255
fi

