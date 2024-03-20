#!/usr/bin/env bash

### Test etherscan integration

DIR=$(mktemp -d)
cd "$DIR" || exit 255

solc-select use 0.4.25 --always-install

delay_etherscan () {
    # Perform a small sleep when API key is not available (e.g. on PR CI from external contributor)
    if [ "$GITHUB_ETHERSCAN" = "" ]; then
        sleep 5s
    else
      # Always sleep 2 second in the CI
      # We have a lot of concurrent github action so this is needed
      sleep 2s
    fi
}

echo "::group::Etherscan mainnet"
crytic-compile 0x7F37f78cBD74481E593F9C737776F7113d76B315 --compile-remove-metadata --etherscan-apikey "$GITHUB_ETHERSCAN"

if [ $? -ne 0 ]
then
    echo "Etherscan mainnet test failed"
    exit 255
fi
echo "::endgroup::"

delay_etherscan

# From crytic/slither#1154
echo "::group::Etherscan #3"
crytic-compile 0xcfc1E0968CA08aEe88CbF664D4A1f8B881d90f37 --compile-remove-metadata --etherscan-apikey "$GITHUB_ETHERSCAN"

if [ $? -ne 0 ]
then
    echo "Etherscan #3 test failed"
    exit 255
fi
echo "::endgroup::"

delay_etherscan

# From crytic/crytic-compile#415
echo "::group::Etherscan #4"
crytic-compile 0x19c7d0fbf906c282dedb5543d098f43dfe9f856f --compile-remove-metadata --etherscan-apikey "$GITHUB_ETHERSCAN"

if [ $? -ne 0 ]
then
    echo "Etherscan #4 test failed"
    exit 255
fi
echo "::endgroup::"

delay_etherscan

# From crytic/crytic-compile#150
echo "::group::Etherscan #5"
crytic-compile 0x2a311e451491091d2a1d3c43f4f5744bdb4e773a --compile-remove-metadata --etherscan-apikey "$GITHUB_ETHERSCAN"

if [ $? -ne 0 ]
then
    echo "Etherscan #5 test failed"
    case "$(uname -sr)" in
        CYGWIN*|MINGW*|MSYS*)
            echo "This test is known to fail on Windows"
        ;;
        *)
            exit 255
        ;;
    esac
fi
echo "::endgroup::"

delay_etherscan

# From crytic/crytic-compile#151
echo "::group::Etherscan #6"
crytic-compile 0x4c808e3c011514d5016536af11218eec537eb6f5 --compile-remove-metadata --etherscan-apikey "$GITHUB_ETHERSCAN"

if [ $? -ne 0 ]
then
    echo "Etherscan #6 test failed"
    exit 255
fi
echo "::endgroup::"

delay_etherscan

# via-ir test for crytic/crytic-compile#517
echo "::group::Etherscan #7"
crytic-compile 0x9AB6b21cDF116f611110b048987E58894786C244 --compile-remove-metadata --etherscan-apikey "$GITHUB_ETHERSCAN"

if [ $? -ne 0 ]
then
    echo "Etherscan #7 test failed"
    exit 255
fi
echo "::endgroup::"

# From crytic/crytic-compile#544
echo "::group::Etherscan #8"
crytic-compile 0x9AB6b21cDF116f611110b048987E58894786C244 --etherscan-apikey "$GITHUB_ETHERSCAN"

if [ $? -ne 0 ]
then
    echo "Etherscan #8 test failed"
    exit 255
fi

dir_name=$(find crytic-export/etherscan-contracts/ -type d -name "*0x9AB6b21cDF116f611110b048987E58894786C244*" -print -quit)
cd "$dir_name" || { echo "Failed to change directory"; exit 255; }

if [ ! -f crytic_compile.config.json ]; then
    echo "crytic_compile.config.json does not exist"
    exit 255
fi

# TODO: Globbing at crytic_compile.py:720 to run with '.'
crytic-compile 'contracts/InterestRates/InterestRatePositionManager.f.sol' --config-file crytic_compile.config.json

if [ $? -ne 0 ]
then
    echo "crytic-compile command failed"
    exit 255
fi

cd ../../../

echo "::endgroup::"