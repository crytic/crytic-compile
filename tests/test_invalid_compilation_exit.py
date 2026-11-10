"""Tests for the crytic-compile CLI exit code on invalid compilation."""

import sys
from unittest import mock

import pytest

from crytic_compile import __main__ as cli
from crytic_compile.platform import InvalidCompilation


def test_invalid_compilation_exits_one():
    """An invalid compilation must exit 1, not a negative status."""
    with (
        mock.patch.object(cli, "compile_all", side_effect=InvalidCompilation("nope")),
        mock.patch.object(sys, "argv", ["crytic-compile", "missing.sol"]),
    ):
        with pytest.raises(SystemExit) as exc_info:
            cli.main()
    assert exc_info.value.code == 1
