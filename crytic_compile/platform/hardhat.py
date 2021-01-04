"""
Hardhat platform
"""
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple, List

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import convert_filename, extract_name
from crytic_compile.utils.natspec import Natspec
from .abstract_platform import AbstractPlatform

# Handle cycle
from .solc import relative_to_short

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")


class Hardhat(AbstractPlatform):
    """
    Builder platform
    """

    NAME = "Hardhat"
    PROJECT_URL = "https://github.com/nomiclabs/hardhat"
    TYPE = Type.HARDHAT

    # pylint: disable=too-many-locals,too-many-statements
    def compile(self, crytic_compile: "CryticCompile", **kwargs: str):
        """
        Compile the target

        :param kwargs:
        :return:
        """

        hardhat_ignore_compile = kwargs.get("hardhat_ignore_compile", False) or kwargs.get(
            "ignore_compile", False
        )

        cache_directory = kwargs.get("hardhat_cache_directory", "cache")
        config_file = Path(cache_directory, "solidity-files-cache.json")

        build_directory = Path(kwargs.get("hardhat_artifacts_directory", "artifacts"), "build-info")

        hardhat_working_dir = kwargs.get("hardhat_working_dir", None)

        base_cmd = ["hardhat"]
        if not kwargs.get("npx_disable", False):
            base_cmd = ["npx"] + base_cmd

        if not hardhat_ignore_compile:
            cmd = base_cmd + ["compile"]

            LOGGER.info(
                "'%s' running", " ".join(cmd),
            )

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self._target
            )

            stdout_bytes, stderr_bytes = process.communicate()
            stdout, stderr = (
                stdout_bytes.decode(),
                stderr_bytes.decode(),
            )  # convert bytestrings to unicode strings

            LOGGER.info(stdout)
            if stderr:
                LOGGER.error(stderr)

        (compiler, version_from_config, optimized) = _get_version_from_config(config_file)

        crytic_compile.compiler_version = CompilerVersion(
            compiler=compiler, version=version_from_config, optimized=optimized
        )

        skip_filename = crytic_compile.compiler_version.version in [
            f"0.4.{x}" for x in range(0, 10)
        ]

        files = sorted(
            os.listdir(build_directory), key=lambda x: os.path.getmtime(Path(build_directory, x))
        )
        if not files:
            txt = f"`hardhat compile` failed. Can you run it?\n{build_directory} is empty"
            raise InvalidCompilation(txt)

        build_info = Path(build_directory, files[0])
        with open(build_info, encoding="utf8") as file_desc:
            targets_json = json.load(file_desc)["output"]

            if "contracts" in targets_json:
                for original_filename, contracts_info in targets_json["contracts"].items():
                    for original_contract_name, info in contracts_info.items():
                        contract_name = extract_name(original_contract_name)

                        contract_filename = convert_filename(
                            original_filename,
                            relative_to_short,
                            crytic_compile,
                            working_dir=hardhat_working_dir,
                        )

                        crytic_compile.contracts_names.add(contract_name)
                        crytic_compile.contracts_filenames[contract_name] = contract_filename

                        crytic_compile.abis[contract_name] = info["abi"]
                        crytic_compile.bytecodes_init[contract_name] = info["evm"]["bytecode"][
                            "object"
                        ]
                        crytic_compile.bytecodes_runtime[contract_name] = info["evm"][
                            "deployedBytecode"
                        ]["object"]
                        crytic_compile.srcmaps_init[contract_name] = info["evm"]["bytecode"][
                            "sourceMap"
                        ].split(";")
                        crytic_compile.srcmaps_runtime[contract_name] = info["evm"]["bytecode"][
                            "sourceMap"
                        ].split(";")
                        userdoc = info.get("userdoc", {})
                        devdoc = info.get("devdoc", {})
                        natspec = Natspec(userdoc, devdoc)
                        crytic_compile.natspec[contract_name] = natspec

            if "sources" in targets_json:
                for path, info in targets_json["sources"].items():
                    if skip_filename:
                        path = convert_filename(
                            self._target,
                            relative_to_short,
                            crytic_compile,
                            working_dir=hardhat_working_dir,
                        )
                    else:
                        path = convert_filename(
                            path, relative_to_short, crytic_compile, working_dir=hardhat_working_dir
                        )
                    crytic_compile.filenames.add(path)
                    crytic_compile.asts[path.absolute] = info["ast"]

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Check if the target is a hardhat project

        :param target:
        :return:
        """
        hardhat_ignore = kwargs.get("hardhat_ignore", False)
        if hardhat_ignore:
            return False
        return os.path.isfile(os.path.join(target, "hardhat.config.js")) | os.path.isfile(
            os.path.join(target, "hardhat.config.ts")
        )

    def is_dependency(self, path: str) -> bool:
        """
        Check if the target is a dependency

        :param path:
        :return:
        """
        if path in self._cached_dependencies:
            return self._cached_dependencies[path]
        ret = "node_modules" in Path(path).parts
        self._cached_dependencies[path] = ret
        return ret

    def _guessed_tests(self) -> List[str]:
        """
        Guess the potential unit tests commands

        :return:
        """
        return ["hardhat test"]


def _get_version_from_config(config: Path) -> Optional[Tuple[str, str, bool]]:
    """
    :return: (version, optimized)
    """
    if not config.exists():
        raise InvalidCompilation(f"{config} not found")
    with open(config) as config_f:
        config = json.load(config_f)

    # hardhat supports multiple config file, we dont at the moment
    version = list(config["files"].values())[0]["solcConfig"]["version"]

    optimized = list(config["files"].values())[0]["solcConfig"]["settings"]["optimizer"]["enabled"]
    return "solc", version, optimized
