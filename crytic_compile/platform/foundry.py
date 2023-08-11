"""
Foundry platform
"""
import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional
import toml

from crytic_compile.platform.abstract_platform import AbstractPlatform, PlatformConfig
from crytic_compile.platform.types import Type
from crytic_compile.platform.hardhat import hardhat_like_parsing
from crytic_compile.utils.subprocess import run

# Handle cycle
if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")


class Foundry(AbstractPlatform):
    """
    Foundry platform
    """

    NAME = "Foundry"
    PROJECT_URL = "https://github.com/gakonst/foundry"
    TYPE = Type.FOUNDRY

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

        out_directory = kwargs.get("foundry_out_directory", "out")

        if ignore_compile:
            LOGGER.info(
                "--ignore-compile used, if something goes wrong, consider removing the ignore compile flag"
            )

        if not ignore_compile:
            run(
                [
                    "forge",
                    "build",
                    "--build-info",
                ],
                cwd=self._target,
            )

        build_directory = Path(
            self._target,
            out_directory,
            "build-info",
        )

        hardhat_like_parsing(crytic_compile, self._target, build_directory, self._target)

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

        run(["forge", "clean"], cwd=self._target)

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

        return os.path.isfile(os.path.join(target, "foundry.toml"))

    @staticmethod
    def config(working_dir: str) -> Optional[PlatformConfig]:
        """Return configuration data that should be passed to solc, such as remappings.

        Args:
            working_dir (str): path to the working directory

        Returns:
            Optional[PlatformConfig]: Platform configuration data such as optimization, remappings...
        """
        result = PlatformConfig()
        result.remappings = (
            subprocess.run(["forge", "remappings"], stdout=subprocess.PIPE, check=True)
            .stdout.decode("utf-8")
            .replace("\n", " ")
            .strip()
        )
        with open("foundry.toml", "r") as f:
            foundry_toml = toml.loads(f.read())
            default_profile = foundry_toml["profile"]["default"]

            if "solc_version" in default_profile:
                result.solc_version = default_profile["solc_version"]
            if "offline" in default_profile:
                result.offline = default_profile["offline"]
            if "optimizer" in default_profile:
                result.optimizer = default_profile["optimizer"]
            else:
                # Default to true
                result.optimizer = True
            if "optimizer_runs" in default_profile:
                result.optimizer_runs = default_profile["optimizer_runs"]
            else:
                # Default to 200
                result.optimizer_runs = 200
            if "via_ir" in default_profile:
                result.via_ir = default_profile["via_ir"]
            if "allow_paths" in default_profile:
                result.allow_paths = default_profile["allow_paths"]
            if "evm_version" in default_profile:
                result.evm_version = default_profile["evm_version"]
            else:
                # Default to london
                result.evm_version = "london"
            if "src" in default_profile:
                result.src_path = default_profile["src"]
            if "test" in default_profile:
                result.tests_path = default_profile["test"]
            if "libs" in default_profile:
                result.libs_path = default_profile["libs"]
            if "script" in default_profile:
                result.scripts_path = default_profile["script"]

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
        ret = "lib" in Path(path).parts
        self._cached_dependencies[path] = ret
        return ret

    # pylint: disable=no-self-use
    def _guessed_tests(self) -> List[str]:
        """Guess the potential unit tests commands

        Returns:
            List[str]: The guessed unit tests commands
        """
        return ["forge test"]
