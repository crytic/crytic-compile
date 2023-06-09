"""
Test loading from a zip archive
"""
from pathlib import Path
from crytic_compile.utils.zip import load_from_zip

TEST_DIR = Path(__file__).resolve().parent


def test_zip_archive() -> None:
    """This tests the `_load_from_compile_0_0_1` format"""
    zip_file = Path(TEST_DIR, "call_to_variable-all.sol-0.5.8-legacy.zip").as_posix()
    compilations = load_from_zip(zip_file)[0]
    print(len(compilations.compilation_units.values()))
    compilation_unit = list(compilations.compilation_units.values())[0]
    source_unit = list(compilation_unit.source_units.values())[0]
    assert "name" in source_unit.ast and source_unit.ast["name"] == "SourceUnit"
    assert source_unit.abis["C"] == [
        {
            "constant": True,
            "inputs": [],
            "name": "v",
            "outputs": [{"name": "", "type": "uint256"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        }
    ]
    assert (
        source_unit.bytecodes_runtime["C"]
        == "6080604052348015600f57600080fd5b506004361060285760003560e01c80637c2efcba14602d575b600080fd5b60336049565b6040518082815260200191505060405180910390f35b6000548156fea165627a7a72305820e0578222cdaab073bb18ac8a7dea1887831a2ec6d5cd58cb3422a324811074db0029"
    )
    assert source_unit.srcmaps_runtime["C"] == [
        "0:32:1:-",
        "",
        "",
        "",
        "8:9:-1",
        "5:2",
        "",
        "",
        "30:1",
        "27",
        "20:12",
        "5:2",
        "0:32:1",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "16:13",
        "",
        "",
        ":::i",
        ":::-",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        ":::o",
    ]
    assert source_unit.hashes("C") == {"v()": 2083454138}
