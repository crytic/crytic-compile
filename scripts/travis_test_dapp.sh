#!/usr/bin/env bash

### Test dapp integration

# The dapp init process makes a temporary local git repo and needs certain values to be set
git config --global user.email "ci@trailofbits.com"
git config --global user.name "CI User"


sudo ./scripts/install_nix.sh
. "$HOME/.nix-profile/etc/profile.d/nix.sh"

mkdir /tmp/dapp
cd /tmp/dapp || exit 255
curl https://dapp.tools/install | sh

dapp init

crytic-compile . --compile-remove-metadata
if [ $? -ne 0 ]
then
    echo "dapp test failed"
    exit 255
fi

