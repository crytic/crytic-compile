"""Tests for stale-cache hints in `get_line_from_offset` / `get_global_offset_from_line`."""

from pathlib import Path

import pytest

from crytic_compile import CryticCompile
from crytic_compile.crytic_compile import _PLATFORM_CLEAN_HINTS, _stale_cache_hint
from crytic_compile.platform import Type
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.utils.naming import Filename


class _StubPlatform(AbstractPlatform):
    """Minimal `AbstractPlatform` that performs no compilation."""

    NAME = "Hardhat"
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


def _make_filename(tmp_path: Path) -> Filename:
    """Build a `Filename` pointing at an existing on-disk file."""
    src = tmp_path / "Foo.sol"
    src.write_text("contract C{}\n", encoding="utf-8")
    return Filename(
        absolute=str(src),
        used=str(src),
        relative=str(src),
        short=src.name,
    )


def _make_crytic_compile(tmp_path: Path) -> tuple[CryticCompile, Filename]:
    """Build a `CryticCompile` backed by a stub platform and a single source file."""
    filename = _make_filename(tmp_path)
    crytic = CryticCompile(_StubPlatform(str(tmp_path)))
    crytic.src_content = {filename.absolute: Path(filename.absolute).read_text(encoding="utf-8")}
    return crytic, filename


def test_stale_cache_hint_uses_known_platform_command(tmp_path: Path) -> None:
    """Hint surfaces the platform-specific clean command when the platform is recognized."""

    class _Platform:
        NAME = "Hardhat"

    file = _make_filename(tmp_path)
    msg = _stale_cache_hint(file, _Platform())
    assert "stale" in msg
    assert str(file.absolute) in msg
    assert _PLATFORM_CLEAN_HINTS["Hardhat"] in msg


def test_stale_cache_hint_falls_back_for_unknown_platform(tmp_path: Path) -> None:
    """Unknown platform names fall back to a generic recommendation."""

    class _Platform:
        NAME = "MyCustomPlatform"

    file = _make_filename(tmp_path)
    msg = _stale_cache_hint(file, _Platform())
    assert "build directory" in msg
    for command in _PLATFORM_CLEAN_HINTS.values():
        assert command not in msg


def test_stale_cache_hint_handles_missing_platform(tmp_path: Path) -> None:
    """`None` platform still yields a useful message."""
    file = _make_filename(tmp_path)
    msg = _stale_cache_hint(file, None)
    assert "stale" in msg
    assert "build directory" in msg


def test_get_line_from_offset_raises_invalid_compilation(tmp_path: Path) -> None:
    """Out-of-range offset raises `InvalidCompilation` instead of bare `KeyError`."""
    crytic, filename = _make_crytic_compile(tmp_path)

    line, _ = crytic.get_line_from_offset(filename, 0)
    assert line == 1

    with pytest.raises(InvalidCompilation) as excinfo:
        crytic.get_line_from_offset(filename, 10**9)
    assert "stale" in str(excinfo.value)
    assert _PLATFORM_CLEAN_HINTS["Hardhat"] in str(excinfo.value)


def test_get_global_offset_from_line_raises_invalid_compilation(tmp_path: Path) -> None:
    """Out-of-range line raises `InvalidCompilation` with a clean-command hint."""
    crytic, filename = _make_crytic_compile(tmp_path)

    assert crytic.get_global_offset_from_line(filename, 1) == 0

    with pytest.raises(InvalidCompilation) as excinfo:
        crytic.get_global_offset_from_line(filename, 10**9)
    assert "stale" in str(excinfo.value)
    assert _PLATFORM_CLEAN_HINTS["Hardhat"] in str(excinfo.value)
