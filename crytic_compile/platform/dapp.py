"""
Dapp platform. https://github.com/dapphub/dapptools
"""

import glob
import json
import logging
import os
import re
import subprocess
from pathlib import Path

# Cycle dependency
from typing import TYPE_CHECKING, List

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import extract_filename, extract_name, convert_filename

# Handle cycle
from crytic_compile.utils.natspec import Natspec

if TYPE_CHECKING:
    from crytic_compile import CryticCompile, InvalidCompilation

LOGGER = logging.getLogger("CryticCompile")


class Dapp(AbstractPlatform):
    """
    Dapp class
    """

    NAME = "Dapp"
    PROJECT_URL = "https://github.com/dapphub/dapptools"
    TYPE = Type.DAPP

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str):
        """
        Compile the target

        :param crytic_compile:
        :param target:
        :param kwargs:
        :return:
        """

        dapp_ignore_compile = kwargs.get("dapp_ignore_compile", False) or kwargs.get(
            "ignore_compile", False
        )
        directory = os.path.join(self._target, "out")

        if not dapp_ignore_compile:
            _run_dapp(self._target)

        crytic_compile.compiler_version = _get_version(self._target)

        files = glob.glob(directory + "/**/*.sol.json", recursive=True)
        for file in files:
            with open(file, encoding="utf8") as file_desc:
                targets_json = json.load(file_desc)

            if not "contracts" in targets_json:
                continue

            for original_contract_name, info in targets_json["contracts"].items():
                contract_name = extract_name(original_contract_name)
                contract_filename = extract_filename(original_contract_name)
                contract_filename = convert_filename(
                    contract_filename, _relative_to_short, crytic_compile, working_dir=self._target
                )
                crytic_compile.contracts_names.add(contract_name)
                crytic_compile.contracts_filenames[contract_name] = contract_filename
                crytic_compile.abis[contract_name] = json.loads(info["abi"])
                crytic_compile.bytecodes_init[contract_name] = info["bin"]
                crytic_compile.bytecodes_runtime[contract_name] = info["bin-runtime"]
                crytic_compile.srcmaps_init[contract_name] = info["srcmap"].split(";")
                crytic_compile.srcmaps_runtime[contract_name] = info["srcmap-runtime"].split(";")

                userdoc = json.loads(info.get("userdoc", "{}"))
                devdoc = json.loads(info.get("devdoc", "{}"))
                natspec = Natspec(userdoc, devdoc)
                crytic_compile.natspec[contract_name] = natspec

            for path, info in targets_json["sources"].items():
                path = convert_filename(
                    path, _relative_to_short, crytic_compile, working_dir=self._target
                )
                crytic_compile.filenames.add(path)
                crytic_compile.asts[path.absolute] = info["AST"]

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Heuristic used: check if "dapp build" is present in Makefile

        :param target:
        :return:
        """
        dapp_ignore = kwargs.get("dapp_ignore", False)
        if dapp_ignore:
            return False
        makefile = os.path.join(target, "Makefile")
        if os.path.isfile(makefile):
            with open(makefile, encoding="utf8") as file_desc:
                txt = file_desc.read()
                return "dapp build" in txt
        return False

    def is_dependency(self, path: str) -> bool:
        """
        Check if the path is a dependency

        :param path:
        :return:
        """
        return "lib" in Path(path).parts

    def _guessed_tests(self) -> List[str]:
        """
        Guess the potential unit tests commands

        :return:
        """
        return ["dapp test"]


def _run_dapp(target: str):
    """
    Run Dapp

    :param target:
    :return:
    """
    cmd = ["dapp", "build"]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=target)
    except OSError as error:
        raise InvalidCompilation(error)
    _, _ = process.communicate()


def _get_version(target: str) -> CompilerVersion:
    """
    Get the compiler version used

    :param target:
    :return:
    """
    files = glob.glob(target + "/**/*meta.json", recursive=True)
    version = None
    optimized = None
    compiler = "solc"
    for file in files:
        if version is None:
            with open(file, encoding="utf8") as file_desc:
                config = json.load(file_desc)
            if "compiler" in config:
                if "version" in config["compiler"]:
                    version = re.findall(r"\d+\.\d+\.\d+", config["compiler"]["version"])
                    assert version
            if "settings" in config:
                if "optimizer" in config["settings"]:
                    if "enabled" in config["settings"]["optimizer"]:
                        optimized = config["settings"]["optimizer"]["enabled"]

    return CompilerVersion(compiler=compiler, version=version, optimized=optimized)


def _relative_to_short(relative: Path) -> Path:
    """
    Translate relative path to short

    :param relative:
    :return:
    """
    short = relative
    try:
        short = short.relative_to(Path("src"))
    except ValueError:
        try:
            short = short.relative_to("lib")
        except ValueError:
            pass
    return short
