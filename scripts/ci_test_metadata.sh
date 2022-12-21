#!/usr/bin/env bash

### Test metadata parsing

DIR=$(mktemp -d)
cd "$DIR" || exit 255

solc-select use 0.5.12 --always-install

# We'll fetch eh DAI contract and parse it's metadata
echo "from crytic_compile import CryticCompile" > metadata_test.py
echo "crytic_compile_instance = CryticCompile('0x6B175474E89094C44Da98b954EedeAC495271d0F',etherscan_api_key=$GITHUB_ETHERSCAN)" >> metadata_test.py
echo "cu = list(crytic_compile_instance.compilation_units.values())[0]" >> metadata_test.py
echo "metadata_keys = cu.metadata_of('Dai').keys()" >> metadata_test.py
echo "metadata_key1_val = cu.metadata_of('Dai')['bzzr1']" >> metadata_test.py
echo "metadata_key2_val = cu.metadata_of('Dai')['solc']" >> metadata_test.py
echo "print(f\"{','.join(metadata_keys)},{metadata_key1_val},{metadata_key2_val}\")" >> metadata_test.py

expected_output='bzzr1,solc,92df983266c28b6fb4c7c776b695725fd63d55b8cd5d5618b69fb544ce801d85,0.5.12'
output=$(python metadata_test.py)

if [ "$expected_output" != "$output" ]
then
    echo -e "Metadata test failed\nexpected_output: $expected_output\nactual output:   $output"
    exit 255
fi