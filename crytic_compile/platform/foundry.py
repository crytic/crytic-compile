"""
Foundry platform
"""
import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, TypeVar, Union

import json

from crytic_compile.platform.abstract_platform import AbstractPlatform, PlatformConfig
from crytic_compile.platform.types import Type
from crytic_compile.platform.hardhat import hardhat_like_parsing
from crytic_compile.utils.subprocess import run

# Handle cycle
if TYPE_CHECKING:
    from crytic_compile import CryticCompile

T = TypeVar("T")

LOGGER = logging.getLogger("CryticCompile")


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

    # pylint: disable=too-many-locals,too-many-statements,too-many-branches
    def compile(self, crytic_compile: "CryticCompile", **kwargs: str) -> None:
        """Compile

        Args:
            crytic_compile (CryticCompile): CryticCompile object to populate
            **kwargs: optional arguments. Used: "foundry_ignore_compile", "foundry_out_directory"

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
            compilation_command = [
                "forge",
                "build",
                "--build-info",
            ]

            targeted_build = not self._project_root.samefile(self._target)
            if targeted_build:
                compilation_command += [
                    str(Path(self._target).resolve().relative_to(self._project_root))
                ]

            compile_all = kwargs.get("foundry_compile_all", False)

            foundry_config = self.config(self._project_root)

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

        build_directory = Path(
            self._project_root,
            out_directory,
            "build-info",
        )

        hardhat_like_parsing(
            crytic_compile, str(self._target), build_directory, str(self._project_root)
        )

    def clean(self, **kwargs: str) -> None:
        """Clean compilation artifacts

        Args:
            **kwargs: optional arguments.
        """

        ignore_compile = kwargs.get("foundry_ignore_compile", False) or kwargs.get(
            "ignore_compile", False
        )

        if ignore_compile:
            return

        run(["forge", "clean"], cwd=self._project_root)

    @staticmethod
    def locate_project_root(file_or_dir: str) -> Optional[Path]:
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
    def config(working_dir: Union[str, Path]) -> Optional[PlatformConfig]:
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

        return result

    # pylint: disable=no-self-use
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

    # pylint: disable=no-self-use
    def _guessed_tests(self) -> List[str]:
        """Guess the potential unit tests commands

        Returns:
            List[str]: The guessed unit tests commands
        """
        return ["forge test"]
