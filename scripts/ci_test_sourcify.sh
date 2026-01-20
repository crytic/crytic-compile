#!/usr/bin/env bash
set -euo pipefail

### Test Sourcify integration

DIR=$(mktemp -d)
cd "$DIR" || exit 255

solc-select use 0.4.25 --always-install

echo "::group::Sourcify mainnet"
if ! crytic-compile "sourcify-1:0x7F37f78cBD74481E593F9C737776F7113d76B315" --compile-remove-metadata
then
    echo "Sourcify mainnet test failed"
    exit 255
fi
echo "::endgroup::"

# Same as Etherscan #3 - test basic compilation
echo "::group::Sourcify #3"
if ! crytic-compile "sourcify-1:0xcfc1E0968CA08aEe88CbF664D4A1f8B881d90f37" --compile-remove-metadata
then
    echo "Sourcify #3 test failed"
    exit 255
fi
echo "::endgroup::"

# Same as Etherscan #4 - from crytic/crytic-compile#415
echo "::group::Sourcify #4"
if ! crytic-compile "sourcify-1:0x19c7d0fbf906c282dedb5543d098f43dfe9f856f" --compile-remove-metadata
then
    echo "Sourcify #4 test failed"
    exit 255
fi
echo "::endgroup::"

# Same as Etherscan #5 - from crytic/crytic-compile#150
echo "::group::Sourcify #5"
if ! crytic-compile "sourcify-1:0x2a311e451491091d2a1d3c43f4f5744bdb4e773a" --compile-remove-metadata
then
    echo "Sourcify #5 test failed"
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

# Same as Etherscan #6 - from crytic/crytic-compile#151
echo "::group::Sourcify #6"
if ! crytic-compile "sourcify-1:0x4c808e3c011514d5016536af11218eec537eb6f5" --compile-remove-metadata
then
    echo "Sourcify #6 test failed"
    exit 255
fi
echo "::endgroup::"

# Same as Etherscan #7 - via-ir test for crytic/crytic-compile#517
echo "::group::Sourcify #7"
if ! crytic-compile "sourcify-1:0x9AB6b21cDF116f611110b048987E58894786C244" --compile-remove-metadata
then
    echo "Sourcify #7 test failed"
    exit 255
fi
echo "::endgroup::"

# Same as Etherscan #8 - from crytic/crytic-compile#544, test config file generation
echo "::group::Sourcify #8"
if ! crytic-compile "sourcify-1:0x9AB6b21cDF116f611110b048987E58894786C244"
then
    echo "Sourcify #8 test failed"
    exit 255
fi

dir_name=$(find crytic-export/sourcify-contracts/ -type d -name "*0x9AB6b21cDF116f611110b048987E58894786C244*" -print -quit)
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

# Same as Etherscan #9 - test with no verified code - should fail
echo "::group::Sourcify #9"
if crytic-compile "sourcify-1:0xc3898ea7e322b3cdc92d65cfe5a34808b7338236"
then
    echo "Sourcify #9 test failed"
    exit 255
fi
echo "::endgroup::"

# Test hex chain ID format (Sourcify-specific feature)
echo "::group::Sourcify hex chain ID"
if ! crytic-compile "sourcify-0x1:0x7F37f78cBD74481E593F9C737776F7113d76B315" --compile-remove-metadata
then
    echo "Sourcify hex chain ID test failed"
    exit 255
fi
echo "::endgroup::"
