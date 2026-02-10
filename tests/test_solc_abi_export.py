"""
Tests for ABI normalization during solc export.
"""

import json

from crytic_compile.platform.solc import _serialize_abi_for_export


def test_serialize_abi_normalizes_library_signature_types() -> None:
    abi = [
        {
            "type": "function",
            "name": "computeL",
            "inputs": [
                {
                    "name": "positions",
                    "type": "tuple[]",
                    "internalType": "struct NftRef[]",
                    "components": [
                        {
                            "name": "kind",
                            "type": "NftKind",
                            "internalType": "enum NftKind",
                        },
                        {
                            "name": "tokenId",
                            "type": "uint248",
                            "internalType": "uint248",
                        },
                    ],
                },
                {
                    "name": "positionManager",
                    "type": "IPositionManager",
                    "internalType": "contract IPositionManager",
                },
                {
                    "name": "loManager",
                    "type": "ILimitOrderManager",
                    "internalType": "interface ILimitOrderManager",
                },
            ],
            "outputs": [{"name": "", "type": "uint256", "internalType": "uint256"}],
            "stateMutability": "view",
        }
    ]

    exported = json.loads(_serialize_abi_for_export(abi))
    inputs = exported[0]["inputs"]

    assert inputs[0]["components"][0]["type"] == "uint8"
    assert inputs[1]["type"] == "address"
    assert inputs[2]["type"] == "address"
    assert inputs[0]["components"][0]["internalType"] == "enum NftKind"


def test_serialize_abi_preserves_array_suffix_when_normalizing() -> None:
    abi = [
        {
            "type": "function",
            "name": "f",
            "inputs": [
                {"name": "roles", "type": "Role[]", "internalType": "enum Access.Role[]"},
                {
                    "name": "targets",
                    "type": "IModule[2]",
                    "internalType": "contract IModule[2]",
                },
            ],
            "outputs": [],
            "stateMutability": "pure",
        }
    ]

    exported = json.loads(_serialize_abi_for_export(abi))
    inputs = exported[0]["inputs"]

    assert inputs[0]["type"] == "uint8[]"
    assert inputs[1]["type"] == "address[2]"


def test_serialize_abi_handles_json_string_inputs() -> None:
    abi_string = json.dumps(
        [
            {
                "type": "function",
                "name": "g",
                "inputs": [
                    {"name": "a", "type": "MyEnum", "internalType": "enum Foo.MyEnum"},
                    {"name": "b", "type": "IThing", "internalType": "interface IThing"},
                ],
                "outputs": [],
                "stateMutability": "nonpayable",
            }
        ]
    )

    exported = json.loads(_serialize_abi_for_export(abi_string))
    inputs = exported[0]["inputs"]

    assert inputs[0]["type"] == "uint8"
    assert inputs[1]["type"] == "address"
