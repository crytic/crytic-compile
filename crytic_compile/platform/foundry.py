"""
Foundry platform
"""
import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Dict, TypeVar

import toml

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
            compilation_command = [
                "forge",
                "build",
                "--build-info",
            ]

            compile_all = kwargs.get("foundry_compile_all", False)

            if not compile_all:
                foundry_config = self.config(str(crytic_compile.working_dir.absolute()))
                if foundry_config:
                    compilation_command += [
                        "--skip",
                        f"*/{foundry_config.tests_path}/**",
                        f"*/{foundry_config.scripts_path}/**",
                        "--force",
                    ]

            run(
                compilation_command,
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
        with open("foundry.toml", "r", encoding="utf-8") as f:
            foundry_toml = toml.loads(f.read())
            default_profile = foundry_toml["profile"]["default"]

            def lookup_by_keys(keys: List[str], dictionary: Dict[str, T]) -> Optional[T]:
                for key in keys:
                    if key in dictionary:
                        return dictionary[key]
                return None

            # Foundry supports snake and kebab case.
            result.solc_version = lookup_by_keys(
                ["solc", "solc_version", "solc-version"], default_profile
            )
            via_ir = lookup_by_keys(["via_ir", "via-ir"], default_profile)
            if via_ir:
                result.via_ir = via_ir
            result.allow_paths = lookup_by_keys(["allow_paths", "allow-paths"], default_profile)

            if "offline" in default_profile:
                result.offline = default_profile["offline"]
            if "optimizer" in default_profile:
                result.optimizer = default_profile["optimizer"]
            else:
                # Default to true
                result.optimizer = True
            optimizer_runs = lookup_by_keys(["optimizer_runs", "optimizer-runs"], default_profile)
            if optimizer_runs is None:
                # Default to 200
                result.optimizer_runs = 200
            else:
                result.optimizer_runs = optimizer_runs
            evm_version = lookup_by_keys(["evm_version", "evm-version"], default_profile)
            if evm_version is None:
                result.evm_version = evm_version
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
