"""
Foundry platform
"""

import json
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from crytic_compile.platform.abstract_platform import AbstractPlatform, PlatformConfig
from crytic_compile.platform.hardhat import hardhat_like_parsing
from crytic_compile.platform.types import Type
from crytic_compile.utils.subprocess import run

# Handle cycle
if TYPE_CHECKING:
    from crytic_compile import CryticCompile

T = TypeVar("T")

LOGGER = logging.getLogger("CryticCompile")


def _get_forge_version() -> tuple[int, int, int] | None:
    """Get forge version as tuple, or None if unable to parse.

    Returns:
        Version tuple (major, minor, patch) or None if detection fails.
    """
    try:
        result = subprocess.run(
            ["forge", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        versions = re.findall(r"\d+\.\d+\.\d+", result.stdout)
        if versions:
            parts = versions[0].split(".")
            return (int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:  # noqa: BLE001
        pass
    return None


class Foundry(AbstractPlatform):
    """
    Foundry platform
    """

    NAME = "Foundry"
    PROJECT_URL = "https://github.com/foundry-rs/foundry"
    TYPE = Type.FOUNDRY

    def __init__(self, target: str, **_kwargs: str):
        super().__init__(target, **_kwargs)

        project_root = Foundry.locate_project_root(target)
        # if we are initializing this, it is indeed a foundry project and thus has a root path
        assert project_root is not None
        self._project_root: Path = project_root

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str) -> None:
        """Compile

        Args:
            crytic_compile (CryticCompile): CryticCompile object to populate
            **kwargs: optional arguments. Used: "foundry_ignore_compile", "foundry_out_directory",
                "foundry_build_info_directory", "foundry_deny", "foundry_no_force"

        """

        ignore_compile = kwargs.get("foundry_ignore_compile", False) or kwargs.get(
            "ignore_compile", False
        )

        foundry_config = None

        if ignore_compile:
            LOGGER.info(
                "--ignore-compile used, if something goes wrong, consider removing the ignore compile flag"
            )
        else:
            deny_level = kwargs.get("foundry_deny")
            if deny_level is None:
                forge_version = _get_forge_version()
                if forge_version and forge_version >= (1, 4, 0):
                    deny_level = "never"

            compilation_command = [
                "forge",
                "build",
                "--build-info",
            ]

            if deny_level:
                compilation_command.extend(["--deny", deny_level])

            targeted_build = not self._project_root.samefile(self._target)
            if targeted_build:
                compilation_command += [
                    str(Path(self._target).resolve().relative_to(self._project_root))
                ]

            compile_all = kwargs.get("foundry_compile_all", False)
            no_force = kwargs.get("foundry_no_force", False)

            foundry_config = self.config(self._project_root)

            # When no_force is enabled, we must compile all files (including tests)
            # to ensure test changes are detected. Otherwise tests would be skipped
            # and test modifications wouldn't trigger recompilation.
            # We also clean build-info to prevent multiple compilation units from accumulating.
            if no_force:
                compile_all = True
                out_dir = foundry_config.out_path if foundry_config else "out"
                build_info_dir = Path(self._project_root, out_dir, "build-info")
                if build_info_dir.exists():
                    shutil.rmtree(build_info_dir)
                    LOGGER.info("Cleaned %s for fresh build-info generation", build_info_dir)

            if not targeted_build and not compile_all and foundry_config:
                compilation_command += [
                    "--skip",
                    f"./{foundry_config.tests_path}/**",
                    f"./{foundry_config.scripts_path}/**",
                    "--force",
                ]

            run(
                compilation_command,
                cwd=self._project_root,
            )

        out_directory_detected = foundry_config.out_path if foundry_config else "out"
        out_directory_config = kwargs.get("foundry_out_directory", None)
        out_directory = out_directory_config if out_directory_config else out_directory_detected

        # Determine build-info directory: CLI override > forge config > default
        build_info_override = kwargs.get("foundry_build_info_directory", None)
        if build_info_override:
            build_directory = Path(self._project_root, build_info_override)
        elif foundry_config and foundry_config.build_info_path:
            build_directory = Path(self._project_root, foundry_config.build_info_path)
        else:
            build_directory = Path(self._project_root, out_directory, "build-info")

        hardhat_like_parsing(
            crytic_compile, str(self._target), build_directory, str(self._project_root)
        )

    def clean(self, **kwargs: str) -> None:
        """Clean compilation artifacts

        Args:
            **kwargs: optional arguments. Used: "foundry_ignore_compile", "ignore_compile",
                "foundry_no_force"
        """
        ignore_compile = kwargs.get("foundry_ignore_compile", False) or kwargs.get(
            "ignore_compile", False
        )
        no_force = kwargs.get("foundry_no_force", False)

        # Skip cleaning when using incremental compilation mode
        if ignore_compile or no_force:
            return

        run(["forge", "clean"], cwd=self._project_root)

    @staticmethod
    def locate_project_root(file_or_dir: str) -> Path | None:
        """Determine the project root (if the target is a Foundry project)

        Foundry projects are detected through the presence of their
        configuration file. See the following for reference:

        https://github.com/foundry-rs/foundry/blob/6983a938580a1eb25d9dbd61eb8cad8cd137a86d/crates/config/README.md#foundrytoml

        Args:
            file_or_dir (str): path to the target

        Returns:
            Optional[Path]: path to the project root, if found
        """

        target = Path(file_or_dir).resolve()

        # if the target is a directory, see if it has a foundry config
        if target.is_dir() and (target / "foundry.toml").is_file():
            return target

        # if the target is a file, it might be a specific contract
        # within a foundry project. Look in parent directories for a
        # config file
        for p in target.parents:
            if (p / "foundry.toml").is_file():
                return p

        return None

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """Check if the target is a foundry project

        Args:
            target (str): path to the target
            **kwargs: optional arguments. Used: "foundry_ignore"

        Returns:
            bool: True if the target is a foundry project
        """
        if kwargs.get("foundry_ignore", False):
            return False

        return Foundry.locate_project_root(target) is not None

    @staticmethod
    def config(working_dir: str | Path) -> PlatformConfig | None:
        """Return configuration data that should be passed to solc, such as remappings.

        Args:
            working_dir (str): path to the working_dir

        Returns:
            Optional[PlatformConfig]: Platform configuration data such as optimization, remappings...
        """
        result = PlatformConfig()
        LOGGER.info("'forge config --json' running")
        json_config = json.loads(
            subprocess.run(
                ["forge", "config", "--json"], cwd=working_dir, stdout=subprocess.PIPE, check=True
            ).stdout
        )

        # Solc configurations
        result.solc_version = json_config.get("solc")
        result.via_ir = json_config.get("via_ir")
        result.allow_paths = json_config.get("allow_paths")
        result.offline = json_config.get("offline")
        result.evm_version = json_config.get("evm_version")
        result.optimizer = json_config.get("optimizer")
        result.optimizer_runs = json_config.get("optimizer_runs")
        result.remappings = json_config.get("remappings")

        # Foundry project configurations
        result.src_path = json_config.get("src")
        result.tests_path = json_config.get("test")
        result.libs_path = json_config.get("libs")
        result.scripts_path = json_config.get("script")
        result.out_path = json_config.get("out")
        result.build_info_path = json_config.get("build_info_path")

        return result

    def is_dependency(self, path: str) -> bool:
        """Check if the path is a dependency

        Args:
            path (str): path to the target

        Returns:
            bool: True if the target is a dependency
        """
        if path in self._cached_dependencies:
            return self._cached_dependencies[path]
        ret = "lib" in Path(path).parts or "node_modules" in Path(path).parts
        self._cached_dependencies[path] = ret
        return ret

    def _guessed_tests(self) -> list[str]:
        """Guess the potential unit tests commands

        Returns:
            List[str]: The guessed unit tests commands
        """
        return ["forge test"]
