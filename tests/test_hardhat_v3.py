"""Tests for Hardhat 3 source name resolution."""

import json
from pathlib import Path

import pytest

from crytic_compile import CryticCompile
from crytic_compile.platform import Type
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.hardhat import hardhat_like_parsing

# Hardhat 3 source name -> file on disk, relative to the project root
SOURCES = {
    "project/contracts/Main.sol": "contracts/Main.sol",
    "project/test/Harness.sol": "test/Harness.sol",
    # "@openzeppelin/contracts": "4.9.6"
    "npm/@openzeppelin/contracts@4.9.6/access/Ownable.sol": (
        "node_modules/@openzeppelin/contracts/access/Ownable.sol"
    ),
    # "oz-v5": "npm:@openzeppelin/contracts@5.2.0"
    "npm/@openzeppelin/contracts@5.2.0/access/IAccessControl.sol": (
        "node_modules/oz-v5/access/IAccessControl.sol"
    ),
    "npm/dep@1.0.0/Dep.sol": "node_modules/dep/Dep.sol",
    # dep depends on @openzeppelin/contracts@4.4.1, which is in the node_modules folder of dep
    "npm/@openzeppelin/contracts@4.4.1/access/Ownable.sol": (
        "node_modules/dep/node_modules/@openzeppelin/contracts/access/Ownable.sol"
    ),
    # Hardhat finds this package only through the user remapping
    # forge-std/=node_modules/forge-std/src/
    "npm/forge-std@1.9.4/src/Test.sol": "node_modules/forge-std/src/Test.sol",
}

REMAPPINGS = [
    "npm/dep@1.0.0/:@openzeppelin/contracts/=npm/@openzeppelin/contracts@4.4.1/",
    "project/:@openzeppelin/contracts/=npm/@openzeppelin/contracts@4.9.6/",
    "project/:dep/=npm/dep@1.0.0/",
    "project/:forge-std/=npm/forge-std@1.9.4/src/",
    "project/:oz-v5/=npm/@openzeppelin/contracts@5.2.0/",
]


class _StubPlatform(AbstractPlatform):
    """Minimal `AbstractPlatform` that performs no compilation."""

    NAME = "Stub"
    PROJECT_URL = "https://example.invalid"
    TYPE = Type.HARDHAT

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str) -> None:
        return

    def clean(self, **kwargs: str) -> None:
        return

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        return False

    def is_dependency(self, path: str) -> bool:
        return False

    def _guessed_tests(self) -> list[str]:
        return []


@pytest.fixture(name="crytic")
def _parsed_hardhat_v3_project(tmp_path: Path) -> CryticCompile:
    """Parse a Hardhat 3 build-info whose sources exist only at their resolved paths."""
    for path in SOURCES.values():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text("", encoding="utf8")

    build_info = tmp_path / "artifacts" / "build-info"
    build_info.mkdir(parents=True)
    (build_info / "solc-0_8_28-1.json").write_text(
        json.dumps(
            {
                "_format": "hh3-sol-build-info-1",
                "solcVersion": "0.8.28",
                "input": {
                    "language": "Solidity",
                    "settings": {"remappings": REMAPPINGS},
                    "sources": {name: {"content": ""} for name in SOURCES},
                },
            }
        ),
        encoding="utf8",
    )
    (build_info / "solc-0_8_28-1.output.json").write_text(
        json.dumps(
            {"output": {"sources": {name: {"id": i, "ast": {}} for i, name in enumerate(SOURCES)}}}
        ),
        encoding="utf8",
    )

    crytic = CryticCompile(_StubPlatform(str(tmp_path)))
    hardhat_like_parsing(crytic, str(tmp_path), build_info, str(tmp_path))
    return crytic


@pytest.mark.parametrize(("source_name", "path"), SOURCES.items())
def test_hardhat_v3_source_name_resolves_to_installed_file(
    crytic: CryticCompile, tmp_path: Path, source_name: str, path: str
) -> None:
    """Each source name maps to the file that Hardhat compiled."""
    assert crytic.filename_lookup(source_name).absolute == (tmp_path / path).as_posix()
