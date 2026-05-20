"""Tests for _locate_framework_root — the upward platform-discovery helper."""

from pathlib import Path

from crytic_compile.crytic_compile import _locate_framework_root
from crytic_compile.platform.foundry import Foundry
from crytic_compile.platform.hardhat import Hardhat


def test_hardhat_detected_from_nested_subdirectory(tmp_path: Path) -> None:
    """A Hardhat project should be detected even when walking up from a
    nested subdirectory."""
    (tmp_path / "hardhat.config.js").write_text("module.exports = {};")
    nested = tmp_path / "contracts" / "tokens"
    nested.mkdir(parents=True)
    source = nested / "Token.sol"
    source.write_text("contract Token {}")

    platform, root = _locate_framework_root(nested, str(source))
    assert isinstance(platform, Hardhat)
    assert root == tmp_path.resolve()


def test_foundry_detected_from_project_root(tmp_path: Path) -> None:
    """Foundry should still be detected at the working directory itself."""
    (tmp_path / "foundry.toml").write_text("[profile.default]\n")
    source = tmp_path / "src" / "Token.sol"
    source.parent.mkdir()
    source.write_text("contract Token {}")

    platform, root = _locate_framework_root(tmp_path, str(source))
    assert isinstance(platform, Foundry)
    assert root == tmp_path.resolve()


def test_returns_none_when_no_framework_found(tmp_path: Path) -> None:
    """If no framework exists on the path to /, return (None, None)."""
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)

    platform, root = _locate_framework_root(nested, "unused.sol")
    assert platform is None
    assert root is None


def test_respects_ignore_flag(tmp_path: Path) -> None:
    """Passing the platform's ignore flag should prevent detection."""
    (tmp_path / "hardhat.config.js").write_text("module.exports = {};")
    nested = tmp_path / "contracts"
    nested.mkdir()

    platform, root = _locate_framework_root(nested, "unused.sol", hardhat_ignore="true")
    assert platform is None
    assert root is None
