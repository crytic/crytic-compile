#!/usr/bin/env bash
set -euo pipefail

### Test Blockscout integration (no API key required)
# Add new entries here when a chain is added to SUPPORTED_NETWORK_BLOCKSCOUT in blockscout.py

TARGETS=(
    "flow:0xd3bF53DAC106A0290B0483EcBC89d40FcC961f3e"
    "ink:0x4200000000000000000000000000000000000006"
    "metis:0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000"
    "plume:0x4052ACe931bbc647193D23e3442f8688A5845A18"
    "story:0x1514000000000000000000000000000000000000"
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
