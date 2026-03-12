#!/usr/bin/env bash
set -euo pipefail

### Test Blockscout integration (no API key required)
# Target format: blockscout-<chainid>:0x<address>

TARGETS=(
    "blockscout-747:0xd3bF53DAC106A0290B0483EcBC89d40FcC961f3e"
    "blockscout-57073:0x4200000000000000000000000000000000000006"
    "blockscout-1088:0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000"
    "blockscout-98866:0x4052ACe931bbc647193D23e3442f8688A5845A18"
    "blockscout-1514:0x1514000000000000000000000000000000000000"
)

for target in "${TARGETS[@]}"; do
    echo "::group::Blockscout $target"
    if ! crytic-compile "$target" --compile-remove-metadata
    then
        echo "Blockscout $target test failed"
        exit 255
    fi
    echo "::endgroup::"
done
