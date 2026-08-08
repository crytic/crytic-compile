"""Tests for `--compile-custom-build` (issue #423)."""

from pathlib import Path

from crytic_compile import CryticCompile
from crytic_compile.platform import Type
from crytic_compile.platform.abstract_platform import AbstractPlatform


class _RecordingPlatform(AbstractPlatform):
    NAME = "Hardhat"
    PROJECT_URL = "https://example.invalid"
    TYPE = Type.HARDHAT

    def __init__(self, target: str, **kwargs: str) -> None:
        super().__init__(target, **kwargs)
        self.compile_calls: list[dict] = []
        self.clean_calls = 0

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str) -> None:
        self.compile_calls.append(dict(kwargs))

    def clean(self, **kwargs: str) -> None:
        self.clean_calls += 1

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        return False

    def is_dependency(self, path: str) -> bool:
        return False

    def _guessed_tests(self) -> list[str]:
        return []


def test_custom_build_still_parses_artifacts(tmp_path: Path) -> None:
    marker = tmp_path / "built.txt"
    platform = _RecordingPlatform(str(tmp_path))
    CryticCompile(
        platform,
        compile_custom_build=f"python3 -c open(r'{marker}','w').write('1')",
    )
    assert marker.exists(), "custom build command did not run"
    assert platform.compile_calls, "platform.compile() was never called: no compilation units"
    assert platform.compile_calls[0].get("ignore_compile"), (
        "artifacts were rebuilt instead of parsed"
    )
    assert platform.clean_calls == 0, "custom build must not trigger a clean"
