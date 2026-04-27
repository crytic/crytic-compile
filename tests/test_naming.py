"""Tests for filename resolution error messages."""

from pathlib import Path

import pytest

from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.utils.naming import (
    _looks_like_npm_import,
    _unknown_file_message,
    _verify_filename_existence,
)


def test_unknown_file_error_includes_path_and_ls_hint(tmp_path: Path) -> None:
    """Error includes the requested filename and an `ls` hint."""
    missing = Path("nonexistent/Foo.sol")
    with pytest.raises(InvalidCompilation) as excinfo:
        _verify_filename_existence(missing, tmp_path)
    msg = str(excinfo.value)
    assert "Unknown file" in msg
    assert str(missing) in msg
    assert "ls " in msg


def test_unknown_file_error_npm_scoped_hint(tmp_path: Path) -> None:
    """Scoped package imports surface the npm/yarn install hint."""
    missing = Path("@openzeppelin/contracts/token/ERC20/ERC20.sol")
    with pytest.raises(InvalidCompilation) as excinfo:
        _verify_filename_existence(missing, tmp_path)
    msg = str(excinfo.value)
    assert "npm install" in msg
    assert "yarn install" in msg
    assert str(tmp_path) in msg


def test_unknown_file_error_bare_package_hint(tmp_path: Path) -> None:
    """Bare-name imports (e.g. `solmate/...`) surface the install hint."""
    missing = Path("solmate/src/tokens/ERC20.sol")
    msg = _unknown_file_message(missing, tmp_path)
    assert "npm install" in msg


def test_unknown_file_error_project_dir_no_hint(tmp_path: Path) -> None:
    """Local project source paths (`contracts/...`) do not surface npm hint."""
    msg = _unknown_file_message(Path("contracts/Foo.sol"), tmp_path)
    assert "npm install" not in msg
    assert "Unknown file" in msg


def test_unknown_file_error_relative_no_hint(tmp_path: Path) -> None:
    """Explicit relative paths (`./Foo.sol`) do not surface npm hint."""
    msg = _unknown_file_message(Path("./Foo.sol"), tmp_path)
    assert "npm install" not in msg


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("@openzeppelin/contracts/token/ERC20.sol", True),
        ("solmate/src/tokens/ERC20.sol", True),
        ("contracts/Foo.sol", False),
        ("src/Foo.sol", False),
        ("lib/forge-std/src/Test.sol", False),
        ("./Foo.sol", False),
        ("../Foo.sol", False),
        ("Foo.sol", False),
        ("/abs/path/Foo.sol", False),
    ],
)
def test_looks_like_npm_import(path: str, expected: bool) -> None:
    """Classifier covers scoped/bare/project/relative/absolute cases."""
    assert _looks_like_npm_import(Path(path)) is expected
