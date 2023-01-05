#!/usr/bin/env bash

### Test dapp integration

# work around having two python versions loading libraries from each other in CI
OLD_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
alias crytic-compile='LD_LIBRARY_PATH=$OLD_LD_LIBRARY_PATH crytic-compile'
unset LD_LIBRARY_PATH

DIR=$(mktemp -d)
cd "$DIR" || exit 255

# The dapp init process makes a temporary local git repo and needs certain values to be set
git config --global user.email "ci@trailofbits.com"
git config --global user.name "CI User"

which nix-env || exit 255

git clone --recursive https://github.com/dapphub/dapptools "$HOME/.dapp/dapptools"
nix-env -f "$HOME/.dapp/dapptools" -iA dapp seth solc hevm ethsign

dapp init

crytic-compile . --compile-remove-metadata
if [ $? -ne 0 ]
then
    echo "dapp test failed"
    exit 255
fi

