"""Tests for Blockscout platform chain support."""

import pathlib

import pytest

from crytic_compile import CryticCompile

# One verified contract address per Blockscout chain ID.
BLOCKSCOUT_TEST_CONTRACTS: dict[str, str] = {
    "747": "0xd3bF53DAC106A0290B0483EcBC89d40FcC961f3e",  # Flow: WFLOW
    "57073": "0x4200000000000000000000000000000000000006",  # Ink: WETH
    "1088": "0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000",  # Metis: MVM_Coinbase
    "98866": "0x4052ACe931bbc647193D23e3442f8688A5845A18",  # Plume: LendRewards
    "1514": "0x1514000000000000000000000000000000000000",  # Story: WIP
}


@pytest.mark.parametrize("chain_id", sorted(BLOCKSCOUT_TEST_CONTRACTS.keys()))
def test_blockscout_chain(chain_id: str, tmp_path: pathlib.Path) -> None:
    """Verify that each Blockscout network can fetch and compile a known contract."""
    addr = BLOCKSCOUT_TEST_CONTRACTS[chain_id]
    target = f"blockscout-{chain_id}:{addr}"

    cc = CryticCompile(target, export_dir=str(tmp_path))
    assert cc.compilation_units, f"No compilation units produced for {target}"
