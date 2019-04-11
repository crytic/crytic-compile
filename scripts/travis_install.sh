#!/usr/bin/env bash
python setup.py install

function install_solc {
    sudo wget -O /usr/bin/solc-0.5.7 https://github.com/ethereum/solidity/releases/download/v0.5.1/solc-static-linux
    sudo chmod +x /usr/bin/solc-0.5.7

    sudo cp /usr/bin/solc-0.5.7 /usr/bin/solc
}

install_solc
