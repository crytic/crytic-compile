"""Tests for Foundry.is_dependency — dependency classification must be relative to the
project root, not fooled by a parent directory that happens to be named `lib`/`node_modules`
(the normal layout when the project is a git submodule, e.g. ``<repo>/lib/<project>``)."""

from pathlib import Path

from crytic_compile.platform.abstract_platform import PlatformConfig
from crytic_compile.platform.foundry import Foundry


def _make_project(root: Path) -> None:
    """Create a minimal Foundry project at ``root`` with one source and one lib dependency."""
    (root / "src").mkdir(parents=True)
    (root / "foundry.toml").write_text("[profile.default]\n")
    (root / "src" / "Token.sol").write_text("contract Token {}")
    (root / "lib" / "solady").mkdir(parents=True)
    (root / "lib" / "solady" / "Solady.sol").write_text("contract Solady {}")


def test_is_dependency_not_fooled_by_parent_lib_directory(tmp_path: Path) -> None:
    """A project checked out under a parent ``lib/`` directory must still treat its own
    ``src`` as project code, while its own ``lib/`` contracts remain dependencies."""
    project = tmp_path / "lib" / "myproject"  # project nested under a parent "lib/"
    _make_project(project)

    foundry = Foundry(str(project))
    foundry._config = PlatformConfig()  # avoid spawning `forge config --json`

    src_file = project / "src" / "Token.sol"
    dep_file = project / "lib" / "solady" / "Solady.sol"

    # Source under a parent "lib/" is NOT a dependency (the bug flags it because the
    # absolute path contains a "lib" component).
    assert foundry.is_dependency(str(src_file)) is False
    # The project's own lib/ contracts ARE dependencies.
    assert foundry.is_dependency(str(dep_file)) is True
