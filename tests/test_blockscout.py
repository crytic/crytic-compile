"""Tests for Blockscout platform chain support."""

import pathlib

import pytest

from crytic_compile import CryticCompile
from crytic_compile.platform.blockscout import SUPPORTED_NETWORK_BLOCKSCOUT

# One verified contract address per Blockscout network key.
# Add an entry here whenever a new chain is added to SUPPORTED_NETWORK_BLOCKSCOUT.
BLOCKSCOUT_TEST_CONTRACTS: dict[str, str] = {
    "flow": "0xd3bF53DAC106A0290B0483EcBC89d40FcC961f3e",  # WFLOW
    "ink": "0x4200000000000000000000000000000000000006",  # WETH
    "metis": "0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000",  # MVM_Coinbase
    "plume": "0x4052ACe931bbc647193D23e3442f8688A5845A18",  # LendRewards
    "story": "0x1514000000000000000000000000000000000000",  # WIP
}


@pytest.mark.parametrize("network", sorted(SUPPORTED_NETWORK_BLOCKSCOUT.keys()))
def test_blockscout_chain(network: str, tmp_path: pathlib.Path) -> None:
    """Verify that each Blockscout network can fetch and compile a known contract."""
    addr = BLOCKSCOUT_TEST_CONTRACTS.get(network)
    if addr is None:
        pytest.skip(f"No test contract registered for '{network}' in BLOCKSCOUT_TEST_CONTRACTS")

    cc = CryticCompile(f"{network}:{addr}", export_dir=str(tmp_path))
    assert cc.compilation_units, f"No compilation units produced for {network}:{addr}"
