"""
Etherlime platform. https://github.com/LimeChain/etherlime
"""

import os
import json
import logging
import subprocess
import glob
import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from crytic_compile.platform.types import Type
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.utils.naming import convert_filename
from crytic_compile.compiler.compiler import CompilerVersion

# Cycle dependency
if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")


def compile(crytic_compile: "CryticCompile", target: str, **kwargs: str):
    """
    Compile the target
    :param crytic_compile:
    :param target:
    :param kwargs:
    :return:
    """

    etherlime_ignore_compile = kwargs.get("etherlime_ignore_compile", False) or kwargs.get("ignore_compile", False)

    crytic_compile.type = Type.ETHERLIME
    build_directory = "build"

    compile_arguments = kwargs.get("etherlime_compile_arguments", None)

    if not etherlime_ignore_compile:
        cmd = ["etherlime", "compile", target]

        if compile_arguments:
            cmd += compile_arguments.split(" ")

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout_bytes, stderr_bytes = process.communicate()
        stdout, stderr = (
            stdout_bytes.decode(),
            stderr_bytes.decode(),
        )  # convert bytestrings to unicode strings

        LOGGER.info(stdout)

        if stderr:
            LOGGER.error(stderr)

    # similar to truffle
    if not os.path.isdir(os.path.join(target, build_directory)):
        raise InvalidCompilation("No truffle build directory found, did you run `truffle compile`?")
    filenames = glob.glob(os.path.join(target, build_directory, "*.json"))

    version = None
    compiler = "solc-js"

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

    crytic_compile.compiler_version = CompilerVersion(
        compiler=compiler, version=version, optimized=_is_optimized(compile_arguments)
    )


def is_etherlime(target: str) -> bool:
    """
    Check if the target is an etherlime project
    :param target:
    :return:
    """
    if os.path.isfile(os.path.join(target, "package.json")):
        with open("package.json", encoding="utf8") as file_desc:
            package = json.load(file_desc)
        if "dependencies" in package:
            return (
                "etherlime-lib" in package["dependencies"] or "etherlime" in package["dependencies"]
            )
    return False


def is_dependency(path: str) -> bool:
    """
    Check if the path is a dependency
    :param path:
    :return:
    """
    return "node_modules" in Path(path).parts


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
