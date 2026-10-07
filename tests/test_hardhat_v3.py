"""Tests for Hardhat 3 source name resolution."""

import json
from pathlib import Path

import pytest

from crytic_compile import CryticCompile
from crytic_compile.platform import Type
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.hardhat import hardhat_like_parsing

# Install directory -> name and version in package.json
PACKAGES = {
    "node_modules/@openzeppelin/contracts": ("@openzeppelin/contracts", "4.9.6"),
    # "oz-v5": "npm:@openzeppelin/contracts@5.2.0"
    "node_modules/oz-v5": ("@openzeppelin/contracts", "5.2.0"),
    "node_modules/dep": ("dep", "1.0.0"),
    # dep depends on @openzeppelin/contracts@4.4.1
    "node_modules/dep/node_modules/@openzeppelin/contracts": ("@openzeppelin/contracts", "4.4.1"),
    "node_modules/forge-std": ("forge-std", "1.9.4"),
    "node_modules/ds-test": ("ds-test", "1.0.0"),
    # forge-std depends on ds-test@2.0.0
    "node_modules/forge-std/node_modules/ds-test": ("ds-test", "2.0.0"),
}

# Hardhat 3 source name -> file on disk, relative to the project root
SOURCES = {
    "project/contracts/Main.sol": "contracts/Main.sol",
    "project/test/Harness.sol": "test/Harness.sol",
    "npm/@openzeppelin/contracts@4.9.6/access/Ownable.sol": (
        "node_modules/@openzeppelin/contracts/access/Ownable.sol"
    ),
    "npm/@openzeppelin/contracts@5.2.0/access/IAccessControl.sol": (
        "node_modules/oz-v5/access/IAccessControl.sol"
    ),
    "npm/dep@1.0.0/Dep.sol": "node_modules/dep/Dep.sol",
    "npm/@openzeppelin/contracts@4.4.1/access/Ownable.sol": (
        "node_modules/dep/node_modules/@openzeppelin/contracts/access/Ownable.sol"
    ),
    "npm/forge-std@1.9.4/src/Test.sol": "node_modules/forge-std/src/Test.sol",
    "npm/ds-test@2.0.0/src/test.sol": "node_modules/forge-std/node_modules/ds-test/src/test.sol",
}

REMAPPINGS = [
    # User remapping oz/=node_modules/oz-v5/. No install directory has the name oz, and
    # the package name finds @openzeppelin/contracts@4.9.6.
    "project/:oz/=npm/@openzeppelin/contracts@5.2.0/",
    "npm/dep@1.0.0/:@openzeppelin/contracts/=npm/@openzeppelin/contracts@4.4.1/",
    "npm/forge-std@1.9.4/:ds-test/=npm/ds-test@2.0.0/",
    "project/:@openzeppelin/contracts/=npm/@openzeppelin/contracts@4.9.6/",
    "project/:dep/=npm/dep@1.0.0/",
    # User remapping forge-std/=node_modules/forge-std/src/
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
    for directory, (name, version) in PACKAGES.items():
        (tmp_path / directory).mkdir(parents=True)
        (tmp_path / directory / "package.json").write_text(
            json.dumps({"name": name, "version": version}), encoding="utf8"
        )
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
