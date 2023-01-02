"""
Truffle platform
"""
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, List

from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import convert_filename, extract_name
from crytic_compile.utils.natspec import Natspec

from .solc import relative_to_short

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

        Raises:
            InvalidCompilation: If foundry failed to run
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
            cmd = [
                "forge",
                "build",
                "--build-info",
                "--force",
            ]

            LOGGER.info(
                "'%s' running",
                " ".join(cmd),
            )

            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self._target,
                executable=shutil.which(cmd[0]),
            ) as process:

                stdout_bytes, stderr_bytes = process.communicate()
                stdout, stderr = (
                    stdout_bytes.decode(),
                    stderr_bytes.decode(),
                )  # convert bytestrings to unicode strings

                LOGGER.info(stdout)
                if stderr:
                    LOGGER.error(stderr)

        build_directory = Path(
            self._target,
            out_directory,
            "build-info",
        )
        files = sorted(
            os.listdir(build_directory), key=lambda x: os.path.getmtime(Path(build_directory, x))
        )
        files = [f for f in files if f.endswith(".json")]
        if not files:
            txt = f"`forge build` failed. Can you run it?\n{build_directory} is empty"
            raise InvalidCompilation(txt)

        for file in files:
            build_info = Path(build_directory, file)

            # The file here should always ends .json, but just in case use ife
            uniq_id = file if ".json" not in file else file[0:-5]
            compilation_unit = CompilationUnit(crytic_compile, uniq_id)

            with open(build_info, encoding="utf8") as file_desc:
                loaded_json = json.load(file_desc)

                targets_json = loaded_json["output"]

                version_from_config = loaded_json["solcVersion"]  # TODO supper vyper
                input_json = loaded_json["input"]
                compiler = "solc" if input_json["language"] == "Solidity" else "vyper"
                optimized = input_json["settings"]["optimizer"]["enabled"]

                compilation_unit.compiler_version = CompilerVersion(
                    compiler=compiler, version=version_from_config, optimized=optimized
                )

                skip_filename = compilation_unit.compiler_version.version in [
                    f"0.4.{x}" for x in range(0, 10)
                ]

                if "contracts" in targets_json:
                    for original_filename, contracts_info in targets_json["contracts"].items():

                        filename = convert_filename(
                            original_filename,
                            relative_to_short,
                            crytic_compile,
                            working_dir=self._target,
                        )

                        source_unit = compilation_unit.create_source_unit(filename)

                        for original_contract_name, info in contracts_info.items():
                            contract_name = extract_name(original_contract_name)

                            source_unit.contracts_names.add(contract_name)
                            compilation_unit.filename_to_contracts[filename].add(contract_name)

                            source_unit.abis[contract_name] = info["abi"]
                            source_unit.bytecodes_init[contract_name] = info["evm"]["bytecode"][
                                "object"
                            ]
                            source_unit.bytecodes_runtime[contract_name] = info["evm"][
                                "deployedBytecode"
                            ]["object"]
                            source_unit.srcmaps_init[contract_name] = info["evm"]["bytecode"][
                                "sourceMap"
                            ].split(";")
                            source_unit.srcmaps_runtime[contract_name] = info["evm"][
                                "deployedBytecode"
                            ]["sourceMap"].split(";")
                            userdoc = info.get("userdoc", {})
                            devdoc = info.get("devdoc", {})
                            natspec = Natspec(userdoc, devdoc)
                            source_unit.natspec[contract_name] = natspec

                if "sources" in targets_json:
                    for path, info in targets_json["sources"].items():
                        if skip_filename:
                            path = convert_filename(
                                self._target,
                                relative_to_short,
                                crytic_compile,
                                working_dir=self._target,
                            )
                        else:
                            path = convert_filename(
                                path,
                                relative_to_short,
                                crytic_compile,
                                working_dir=self._target,
                            )

                        source_unit = compilation_unit.create_source_unit(path)
                        source_unit.ast = info["ast"]

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
