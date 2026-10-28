"""Tests for the vyper platform."""

import crytic_compile.platform.vyper as vyper_platform
from crytic_compile import CryticCompile

_VYPER_04_ARTIFACTS = {
    "compiler": "vyper-0.4.3",
    "contracts": {
        "t.vy": {
            "t": {
                "abi": [],
                "userdoc": {},
                "devdoc": {},
                "evm": {
                    "bytecode": {"object": "0x6000"},
                    "deployedBytecode": {
                        "object": "0x6000",
                        "sourceMap": {
                            "pc_pos_map_compressed": "0:152:0:-;-1:-1:-1",
                            "pc_pos_map": {},
                            "pc_jump_map": {},
                        },
                    },
                },
            }
        }
    },
    "sources": {"t.vy": {"ast": {}, "id": 0}},
}


def test_object_source_map_from_vyper_04(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "t.vy"
    target.write_text("x: public(uint256)\n", encoding="utf-8")
    monkeypatch.setattr(
        vyper_platform, "_run_vyper_standard_json", lambda *a, **k: _VYPER_04_ARTIFACTS
    )
    cc = CryticCompile("t.vy")
    (unit,) = cc.compilation_units.values()
    (source_unit,) = unit.source_units.values()
    assert source_unit.srcmaps_runtime["t"] == ["0:152:0:-", "-1:-1:-1"]
