#!/usr/bin/env bash
set -euo pipefail

### Test etherscan integration

DIR=$(mktemp -d)
cd "$DIR" || exit 255

solc-select use 0.4.25 --always-install

# Etherscan now _requires_ an API key, so skip the tests if it's not available
if [ "$ETHERSCAN_API_KEY" = "" ]; then
    echo "API key not available, skipping etherscan tests"
    exit 0
fi

echo "::group::Etherscan mainnet"
if ! crytic-compile 0x7F37f78cBD74481E593F9C737776F7113d76B315 --compile-remove-metadata --etherscan-apikey "$ETHERSCAN_API_KEY"
then
    echo "Etherscan mainnet test failed"
    exit 255
fi
echo "::endgroup::"

# From crytic/slither#1154
# Try without an explicit API key argument, to verify reading `ETHERSCAN_API_KEY` from env works fine
echo "::group::Etherscan #3"
if ! crytic-compile 0xcfc1E0968CA08aEe88CbF664D4A1f8B881d90f37 --compile-remove-metadata
then
    echo "Etherscan #3 test failed"
    exit 255
fi
echo "::endgroup::"

# From crytic/crytic-compile#415
echo "::group::Etherscan #4"
if ! crytic-compile 0x19c7d0fbf906c282dedb5543d098f43dfe9f856f --compile-remove-metadata --etherscan-apikey "$ETHERSCAN_API_KEY"
then
    echo "Etherscan #4 test failed"
    exit 255
fi
echo "::endgroup::"

# From crytic/crytic-compile#150
echo "::group::Etherscan #5"
if ! crytic-compile 0x2a311e451491091d2a1d3c43f4f5744bdb4e773a --compile-remove-metadata --etherscan-apikey "$ETHERSCAN_API_KEY"
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

# From crytic/crytic-compile#151
echo "::group::Etherscan #6"
if ! crytic-compile 0x4c808e3c011514d5016536af11218eec537eb6f5 --compile-remove-metadata --etherscan-apikey "$ETHERSCAN_API_KEY"
then
    echo "Etherscan #6 test failed"
    exit 255
fi
echo "::endgroup::"

# via-ir test for crytic/crytic-compile#517
echo "::group::Etherscan #7"
if ! crytic-compile 0x9AB6b21cDF116f611110b048987E58894786C244 --compile-remove-metadata --etherscan-apikey "$ETHERSCAN_API_KEY"
then
    echo "Etherscan #7 test failed"
    exit 255
fi
echo "::endgroup::"

# From crytic/crytic-compile#544
echo "::group::Etherscan #8"
if ! crytic-compile 0x9AB6b21cDF116f611110b048987E58894786C244 --etherscan-apikey "$ETHERSCAN_API_KEY"
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
if ! crytic-compile 'contracts/InterestRates/InterestRatePositionManager.f.sol' --config-file crytic_compile.config.json
then
    echo "crytic-compile command failed"
    exit 255
fi

cd ../../../

echo "::endgroup::"
