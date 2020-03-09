"""
Brownie platform. https://github.com/iamdefinitelyahuman/brownie
"""
import glob
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, TYPE_CHECKING

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import convert_filename, Filename

# Cycle dependency
from crytic_compile.utils.natspec import Natspec

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")


class Brownie(AbstractPlatform):
    """
    Brownie class
    """

    NAME = "Brownie"
    PROJECT_URL = "https://github.com/iamdefinitelyahuman/brownie"
    TYPE = Type.BROWNIE

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str):
        """
        Compile the target

        :param crytic_compile:
        :param target:
        :param kwargs:
        :return:
        """
        build_directory = Path("build", "contracts")
        brownie_ignore_compile = kwargs.get("brownie_ignore_compile", False) or kwargs.get(
            "ignore_compile", False
        )

        base_cmd = ["brownie"]

        if not brownie_ignore_compile:
            cmd = base_cmd + ["compile"]
            try:
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self._target
                )
            except OSError as error:
                raise InvalidCompilation(error)

            stdout_bytes, stderr_bytes = process.communicate()
            stdout, stderr = (
                stdout_bytes.decode(),
                stderr_bytes.decode(),
            )  # convert bytestrings to unicode strings

            LOGGER.info(stdout)
            if stderr:
                LOGGER.error(stderr)

        if not os.path.isdir(os.path.join(self._target, build_directory)):
            raise InvalidCompilation("`brownie compile` failed. Can you run it?")

        filenames = glob.glob(os.path.join(self._target, build_directory, "*.json"))

        _iterate_over_files(crytic_compile, self._target, filenames)

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Check if the target is a brownie env

        :param target:
        :return:
        """
        brownie_ignore = kwargs.get("brownie_ignore", False)
        if brownie_ignore:
            return False
        # < 1.1.0: brownie-config.json
        # >= 1.1.0: brownie-config.yaml
        return os.path.isfile(os.path.join(target, "brownie-config.json")) or os.path.isfile(
            os.path.join(target, "brownie-config.yaml")
        )

    def is_dependency(self, _path: str) -> bool:
        """
        Check if the path is a dependency

        :param _path:
        :return:
        """
        return False

    def _guessed_tests(self) -> List[str]:
        """
        Guess the potential unit tests commands

        :return:
        """
        return ["brownie test"]


def _iterate_over_files(crytic_compile: "CryticCompile", target: str, filenames: List[str]):
    """
    Iterate over the files

    :param crytic_compile:
    :param target:
    :param filenames:
    :return:
    """
    optimized = None
    compiler = "solc"
    version = None

    for original_filename in filenames:
        with open(original_filename, encoding="utf8") as f_file:
            target_loaded: Dict = json.load(f_file)

            if not "ast" in target_loaded:
                continue

            if optimized is None:
                if compiler in target_loaded:
                    compiler_d: Dict = target_loaded["compiler"]
                    optimized = compiler_d.get("optimize", False)
                    version = _get_version(compiler_d)

            filename_txt = target_loaded["ast"]["absolutePath"]
            filename: Filename = convert_filename(
                filename_txt, _relative_to_short, crytic_compile, working_dir=target
            )

            crytic_compile.asts[filename.absolute] = target_loaded["ast"]
            crytic_compile.filenames.add(filename)
            contract_name = target_loaded["contractName"]
            crytic_compile.contracts_filenames[contract_name] = filename
            crytic_compile.contracts_names.add(contract_name)
            crytic_compile.abis[contract_name] = target_loaded["abi"]
            crytic_compile.bytecodes_init[contract_name] = target_loaded["bytecode"].replace(
                "0x", ""
            )
            crytic_compile.bytecodes_runtime[contract_name] = target_loaded[
                "deployedBytecode"
            ].replace("0x", "")
            crytic_compile.srcmaps_init[contract_name] = target_loaded["sourceMap"].split(";")
            crytic_compile.srcmaps_runtime[contract_name] = target_loaded[
                "deployedSourceMap"
            ].split(";")

            userdoc = target_loaded.get("userdoc", {})
            devdoc = target_loaded.get("devdoc", {})
            natspec = Natspec(userdoc, devdoc)
            crytic_compile.natspec[contract_name] = natspec

    crytic_compile.compiler_version = CompilerVersion(
        compiler=compiler, version=version, optimized=optimized
    )


def _get_version(compiler: Dict) -> str:
    """
    Parse the compiler version

    :param compiler:
    :return:
    """
    version = compiler.get("version", "")
    version = version[len("Version: ") :]
    version = version[0 : version.find("+")]
    return version


def _relative_to_short(relative: Path) -> Path:
    """
    Translate relative path to short (do nothing)

    :param relative:
    :return:
    """
    return relative
