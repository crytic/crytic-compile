"""Tests for the Foundry compilation platform."""

from pathlib import Path
from unittest import mock

from crytic_compile.platform.abstract_platform import PlatformConfig
from crytic_compile.platform.foundry import Foundry


def test_compile_disables_dynamic_test_linking(tmp_path: Path) -> None:
    """Foundry builds should disable dynamic test linking through configuration."""
    (tmp_path / "foundry.toml").write_text("[profile.default]\n", encoding="utf8")
    platform = Foundry(str(tmp_path))
    platform._config = PlatformConfig()

    with (
        mock.patch("crytic_compile.platform.foundry._get_forge_version", return_value=None),
        mock.patch("crytic_compile.platform.foundry.run") as run,
        mock.patch("crytic_compile.platform.foundry.hardhat_like_parsing"),
    ):
        platform.compile(mock.sentinel.crytic_compile, foundry_compile_all=True)

    assert run.call_args.args[0] == ["forge", "build", "--build-info"]
    assert run.call_args.kwargs["extra_env"] == {"FOUNDRY_DYNAMIC_TEST_LINKING": "false"}
