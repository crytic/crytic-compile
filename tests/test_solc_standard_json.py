"""
Tests for the SolcStandardJson platform.
"""

import json
from unittest import mock

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.solc_standard_json import run_solc_standard_json


def _fake_popen(stdout: bytes):
    """Build a mock subprocess.Popen replacement returning the given stdout."""
    fake_proc = mock.MagicMock()
    fake_proc.communicate.return_value = (stdout, b"")
    fake_ctx = mock.MagicMock()
    fake_ctx.__enter__.return_value = fake_proc
    fake_ctx.__exit__.return_value = False
    return mock.MagicMock(return_value=fake_ctx)


def test_run_solc_standard_json_uses_default_compiler() -> None:
    """When no `solc` kwarg is passed, the binary from CompilerVersion is used."""
    compiler_version = CompilerVersion(compiler="solc", version="0.8.0", optimized=False)
    fake_popen = _fake_popen(json.dumps({"contracts": {}}).encode("utf-8"))

    with mock.patch("crytic_compile.platform.solc_standard_json.subprocess.Popen", fake_popen):
        run_solc_standard_json({"language": "Solidity"}, compiler_version)

    cmd = fake_popen.call_args.args[0]
    assert cmd[0] == "solc"


def test_run_solc_standard_json_respects_custom_solc_path() -> None:
    """A custom `solc` path is used as the executable instead of `compiler_version.compiler`."""
    compiler_version = CompilerVersion(compiler="solc", version="0.8.33", optimized=False)
    custom_path = "/custom/path/to/solc-0.8.33"
    fake_popen = _fake_popen(json.dumps({"contracts": {}}).encode("utf-8"))

    with mock.patch("crytic_compile.platform.solc_standard_json.subprocess.Popen", fake_popen):
        run_solc_standard_json({"language": "Solidity"}, compiler_version, solc=custom_path)

    cmd = fake_popen.call_args.args[0]
    assert cmd[0] == custom_path


def test_run_solc_standard_json_merges_solc_env() -> None:
    """Extra env vars from `solc_env` are merged into the subprocess environment."""
    compiler_version = CompilerVersion(compiler="solc", version="0.8.0", optimized=False)
    fake_popen = _fake_popen(json.dumps({"contracts": {}}).encode("utf-8"))

    with mock.patch("crytic_compile.platform.solc_standard_json.subprocess.Popen", fake_popen):
        run_solc_standard_json(
            {"language": "Solidity"},
            compiler_version,
            solc_env={"FOO": "bar"},
        )

    env = fake_popen.call_args.kwargs["env"]
    assert env["FOO"] == "bar"
    assert env["SOLC_VERSION"] == "0.8.0"
