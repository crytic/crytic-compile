#!/usr/bin/env bash

### Test dapp integration

mkdir test_dapp
cd test_dapp


curl https://nixos.org/nix/install | sh
. "$HOME/.nix-profile/etc/profile.d/nix.sh"
git clone --recursive https://github.com/dapphub/dapptools $HOME/.dapp/dapptools
nix-env -f $HOME/.dapp/dapptools -iA dapp seth solc hevm ethsign

dapp init

crytic-compile .

DIFF=$(diff crytic-export/contracts.json ../tests/expected/dapp-demo.json)
if [ "$DIFF" != "" ]
then  
    echo "Dapp test failed"
    echo $DIFF
    exit -1
fi

