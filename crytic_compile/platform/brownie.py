"""
Brownie platform. https://github.com/iamdefinitelyahuman/brownie
"""
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List

from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import Filename, convert_filename

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

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str) -> None:
        """Run the compilation

        Args:
            crytic_compile (CryticCompile): Associated CryticCompile object
            **kwargs: optional arguments. Used "brownie_ignore_compile", "ignore_compile"

        Raises:
            InvalidCompilation: If brownie failed to run
        """
        build_directory = Path("build", "contracts")
        brownie_ignore_compile = kwargs.get("brownie_ignore_compile", False) or kwargs.get(
            "ignore_compile", False
        )

        base_cmd = ["brownie"]

        if not brownie_ignore_compile:
            cmd = base_cmd + ["compile"]
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

        if not os.path.isdir(os.path.join(self._target, build_directory)):
            raise InvalidCompilation("`brownie compile` failed. Can you run it?")

        filenames = list(Path(self._target, build_directory).rglob("*.json"))

        _iterate_over_files(crytic_compile, Path(self._target), filenames)

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """Check if the target is a brownie project

        Args:
            target (str): path to the target
            **kwargs: optional arguments. Used "brownie_ignore"

        Returns:
            bool: True if the target is a brownie project
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
        """Check if the path is a dependency (not supported for brownie)

        Args:
            _path (str): path to the target

        Returns:
            bool: True if the target is a dependency
        """
        return False

    def _guessed_tests(self) -> List[str]:
        """Guess the potential unit tests commands

        Returns:
            List[str]: The guessed unit tests commands
        """
        return ["brownie test"]


# pylint: disable=too-many-locals
def _iterate_over_files(
    crytic_compile: "CryticCompile", target: Path, filenames: List[Path]
) -> None:
    """Iterates over the files and populates the information into the CryticCompile object

    Args:
        crytic_compile (CryticCompile): associated cryticCompile object
        target (Path): path to the target
        filenames (List[Path]): List of files to iterate over
    """
    optimized = None
    compiler = "solc"
    version = None

    compilation_unit = CompilationUnit(crytic_compile, str(target))

    for original_filename in filenames:
        with open(original_filename, encoding="utf8") as f_file:
            target_loaded: Dict = json.load(f_file)

            if "ast" not in target_loaded:
                continue

            if optimized is None:
                # Old brownie
                if compiler in target_loaded:
                    compiler_d: Dict = target_loaded["compiler"]
                    optimized = compiler_d.get("optimize", False)
                    version = _get_version(compiler_d)
                if "compiler" in target_loaded:
                    compiler_d = target_loaded["compiler"]
                    optimized = compiler_d.get("optimize", False)
                    version = _get_version(compiler_d)

            # Filter out vyper files
            if "absolutePath" not in target_loaded["ast"]:
                continue

            filename_txt = target_loaded["ast"]["absolutePath"]
            filename: Filename = convert_filename(
                filename_txt, _relative_to_short, crytic_compile, working_dir=target
            )

            compilation_unit.asts[filename.absolute] = target_loaded["ast"]
            compilation_unit.filenames.add(filename)
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
        compiler=compiler, version=version, optimized=optimized
    )


def _get_version(compiler: Dict) -> str:
    """Parse the compiler version

    Args:
        compiler (Dict): dictionary from the json

    Returns:
        str: Compiler version
    """
    version = compiler.get("version", "")
    version = version[len("Version: ") :]
    version = version[0 : version.find("+")]
    return version


def _relative_to_short(relative: Path) -> Path:
    """Translate relative path to short (do nothing for brownie)

    Args:
        relative (Path): path to the target

    Returns:
        Path: Translated path
    """
    return relative
