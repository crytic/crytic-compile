"""
Truffle platform
"""
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, List, Tuple, Optional

from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import convert_filename
from crytic_compile.utils.natspec import Natspec

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
                "--extra-output",
                "abi",
                "--extra-output",
                "userdoc",
                "--extra-output",
                "devdoc",
                "--extra-output",
                "evm.methodIdentifiers",
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

        filenames = Path(self._target, out_directory).rglob("*.json")

        # foundry only support solc for now
        compiler = "solc"
        compilation_unit = CompilationUnit(crytic_compile, str(self._target))

        for filename_txt in filenames:
            with open(filename_txt, encoding="utf8") as file_desc:
                target_loaded = json.load(file_desc)

                userdoc = target_loaded.get("userdoc", {})
                devdoc = target_loaded.get("devdoc", {})
                natspec = Natspec(userdoc, devdoc)

                if not "ast" in target_loaded:
                    continue

                filename = target_loaded["ast"]["absolutePath"]

                try:
                    filename = convert_filename(
                        filename, lambda x: x, crytic_compile, working_dir=self._target
                    )
                except InvalidCompilation as i:
                    txt = str(i)
                    txt += "\nSomething went wrong, please open an issue in https://github.com/crytic/crytic-compile"
                    # pylint: disable=raise-missing-from
                    raise InvalidCompilation(txt)

                compilation_unit.asts[filename.absolute] = target_loaded["ast"]
                crytic_compile.filenames.add(filename)
                compilation_unit.filenames.add(filename)

                contract_name = filename_txt.parts[-1]
                contract_name = contract_name[: -len(".json")]

                compilation_unit.natspec[contract_name] = natspec
                compilation_unit.filename_to_contracts[filename].add(contract_name)
                compilation_unit.contracts_names.add(contract_name)
                compilation_unit.abis[contract_name] = target_loaded["abi"]
                compilation_unit.bytecodes_init[contract_name] = target_loaded["bytecode"][
                    "object"
                ].replace("0x", "")
                compilation_unit.bytecodes_runtime[contract_name] = target_loaded[
                    "deployedBytecode"
                ]["object"].replace("0x", "")
                compilation_unit.srcmaps_init[contract_name] = target_loaded["bytecode"][
                    "sourceMap"
                ].split(";")
                compilation_unit.srcmaps_runtime[contract_name] = target_loaded["deployedBytecode"][
                    "sourceMap"
                ].split(";")

        version, optimized, runs = _get_config_info(self._target)

        compilation_unit.compiler_version = CompilerVersion(
            compiler=compiler, version=version, optimized=optimized, optimize_runs=runs
        )

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


def _get_config_info(target: str) -> Tuple[str, Optional[bool], Optional[int]]:
    """get the compiler version from solidity-files-cache.json

    Args:
        target (str): path to the project directory

    Returns:
        (str, str, str): compiler version, optimized, runs

    Raises:
        InvalidCompilation: If cache/solidity-files-cache.json cannot be parsed
    """
    config = Path(target, "cache", "solidity-files-cache.json")
    if not config.exists():
        raise InvalidCompilation(
            "Could not find the cache/solidity-files-cache.json file."
            + "If you are using 'cache = true' in foundry's config file, please remove it."
            + " Otherwise please open an issue in https://github.com/crytic/crytic-compile"
        )
    with open(config, "r", encoding="utf8") as config_f:
        config_dict = json.load(config_f)

    version: Optional[str] = None
    optimizer: Optional[bool] = None
    runs: Optional[int] = None

    if "files" in config_dict:
        items = list(config_dict["files"].values())
        # On the form
        # { ..
        #   "artifacts": {
        #      "CONTRACT_NAME": {
        #         "0.8.X+commit...": "filename"}
        #
        if len(items) >= 1:
            item = items[0]
            if "artifacts" in item:
                items_artifact = list(item["artifacts"].values())
                if len(items_artifact) >= 1:
                    item_version = items_artifact[0]
                    version = list(item_version.keys())[0]
                    assert version
                    plus_position = version.find("+")
                    if plus_position > 0:
                        version = version[:plus_position]
            if (
                "solcConfig" in item
                and "settings" in item["solcConfig"]
                and "optimizer" in item["solcConfig"]["settings"]
            ):
                optimizer = item["solcConfig"]["settings"]["optimizer"]["enabled"]
                runs = item["solcConfig"]["settings"]["optimizer"].get("runs", None)

    if version is None:
        raise InvalidCompilation(
            "Something went wrong with cache/solidity-files-cache.json parsing"
            + ". Please open an issue in https://github.com/crytic/crytic-compile"
        )

    return version, optimizer, runs
