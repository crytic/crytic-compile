"""
Etherlime platform. https://github.com/LimeChain/etherlime
"""

import glob
import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import convert_filename

# Cycle dependency
from crytic_compile.utils.natspec import Natspec

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")


class Etherlime(AbstractPlatform):
    """
    Etherlime platform
    """

    NAME = "Etherlime"
    PROJECT_URL = "https://github.com/LimeChain/etherlime"
    TYPE = Type.ETHERLIME

    # pylint: disable=too-many-locals
    def compile(self, crytic_compile: "CryticCompile", **kwargs: str):
        """
        Compile the target

        :param crytic_compile:
        :param target:
        :param kwargs:
        :return:
        """

        etherlime_ignore_compile = kwargs.get("etherlime_ignore_compile", False) or kwargs.get(
            "ignore_compile", False
        )

        build_directory = "build"

        compile_arguments = kwargs.get("etherlime_compile_arguments", None)

        if not etherlime_ignore_compile:
            cmd = ["etherlime", "compile", self._target, "deleteCompiledFiles=true"]

            if not kwargs.get("npx_disable", False):
                cmd = ["npx"] + cmd

            if compile_arguments:
                cmd += compile_arguments.split(" ")

            try:
                with subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self._target
                ) as process:
                    stdout_bytes, stderr_bytes = process.communicate()
                    stdout, stderr = (
                        stdout_bytes.decode(),
                        stderr_bytes.decode(),
                    )  # convert bytestrings to unicode strings

                    LOGGER.info(stdout)

                    if stderr:
                        LOGGER.error(stderr)
            except OSError as error:
                # pylint: disable=raise-missing-from
                raise InvalidCompilation(error)

        # similar to truffle
        if not os.path.isdir(os.path.join(self._target, build_directory)):
            raise InvalidCompilation(
                "No truffle build directory found, did you run `truffle compile`?"
            )
        filenames = glob.glob(os.path.join(self._target, build_directory, "*.json"))

        version = None
        compiler = "solc-js"

        compilation_unit = CompilationUnit(crytic_compile, str(self._target))

        for file in filenames:
            with open(file, encoding="utf8") as file_desc:
                target_loaded = json.load(file_desc)

                if version is None:
                    if "compiler" in target_loaded:
                        if "version" in target_loaded["compiler"]:
                            version = re.findall(
                                r"\d+\.\d+\.\d+", target_loaded["compiler"]["version"]
                            )[0]

                if not "ast" in target_loaded:
                    continue

                filename_txt = target_loaded["ast"]["absolutePath"]
                filename = convert_filename(filename_txt, _relative_to_short, crytic_compile)
                compilation_unit.asts[filename.absolute] = target_loaded["ast"]
                crytic_compile.filenames.add(filename)
                contract_name = target_loaded["contractName"]
                compilation_unit.contracts_filenames[contract_name] = filename
                compilation_unit.contracts_names.add(contract_name)
                compilation_unit.abis[contract_name] = target_loaded["abi"]
                compilation_unit.bytecodes_init[contract_name] = target_loaded["bytecode"].replace(
                    "0x", ""
                )
                compilation_unit.bytecodes_runtime[contract_name] = target_loaded[
                    "deployedBytecode"
                ].replace("0x", "")
                compilation_unit.srcmaps_init[contract_name] = target_loaded["sourceMap"].split(";")
                compilation_unit.srcmaps_runtime[contract_name] = target_loaded[
                    "deployedSourceMap"
                ].split(";")

                userdoc = target_loaded.get("userdoc", {})
                devdoc = target_loaded.get("devdoc", {})
                natspec = Natspec(userdoc, devdoc)
                compilation_unit.natspec[contract_name] = natspec

        compilation_unit.compiler_version = CompilerVersion(
            compiler=compiler, version=version, optimized=_is_optimized(compile_arguments)
        )

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Check if the target is an etherlime project

        :param target:
        :return:
        """
        etherlime_ignore = kwargs.get("etherlime_ignore", False)
        if etherlime_ignore:
            return False
        if os.path.isfile(os.path.join(target, "package.json")):
            with open(os.path.join(target, "package.json"), encoding="utf8") as file_desc:
                package = json.load(file_desc)
            if "dependencies" in package:
                return (
                    "etherlime-lib" in package["dependencies"]
                    or "etherlime" in package["dependencies"]
                )
            if "devDependencies" in package:
                return (
                    "etherlime-lib" in package["devDependencies"]
                    or "etherlime" in package["devDependencies"]
                )
        return False

    def is_dependency(self, path: str) -> bool:
        """
        Check if the path is a dependency

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
        return ["etherlime test"]


def _is_optimized(compile_arguments: Optional[str]) -> bool:
    """
    Check if the optimization is enabled

    :param compile_arguments:
    :return:
    """
    if compile_arguments:
        return "--run" in compile_arguments
    return False


def _relative_to_short(relative: Path) -> Path:
    """
    Translate relative to short

    :param relative:
    :return:
    """
    short = relative
    try:
        short = short.relative_to(Path("contracts"))
    except ValueError:
        try:
            short = short.relative_to("node_modules")
        except ValueError:
            pass
    return short
