"""
Vyper platform
"""
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import convert_filename
from crytic_compile.utils.subprocess import run

# Handle cycle
from crytic_compile.utils.natspec import Natspec

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")


class VyperStandardJson(AbstractPlatform):
    """
    Vyper platform
    """

    NAME = "vyper"
    PROJECT_URL = "https://github.com/vyperlang/vyper"
    TYPE = Type.VYPER
    standard_json_input: Dict = {
        "language": "Vyper",
        "sources": {},
        "settings": {
            "outputSelection": {
                "*": {
                    "*": [
                        "abi",
                        "devdoc",
                        "userdoc",
                        "evm.bytecode",
                        "evm.deployedBytecode",
                        "evm.deployedBytecode.sourceMap",
                    ],
                    "": ["ast"],
                }
            }
        },
    }

    def __init__(self, target: Optional[Path] = None, **_kwargs: str):
        super().__init__(target, **_kwargs)

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str) -> None:
        """Compile the target

        Args:
            crytic_compile (CryticCompile): CryticCompile object to populate
            **kwargs: optional arguments. Used "vyper"


        """
        target = self._target
        # If the target was a directory `add_source_file` should have been called
        # by `compile_all`. Otherwise, we should have a single file target.
        if self._target is not None and os.path.isfile(self._target):
            self.add_source_files([target])

        vyper_bin = kwargs.get("vyper", "vyper")
        compilation_artifacts = None
        with tempfile.NamedTemporaryFile(mode="a+") as f:
            json.dump(self.standard_json_input, f)
            f.seek(0)
            compilation_artifacts = _run_vyper_standard_json(f.name, vyper_bin)

        if "errors" in compilation_artifacts:
            # TODO format errors
            raise InvalidCompilation(compilation_artifacts["errors"])
        compilation_unit = CompilationUnit(crytic_compile, str(target))

        compiler_version = compilation_artifacts["compiler"].split("-")[1]
        assert compiler_version == "0.3.7"
        compilation_unit.compiler_version = CompilerVersion(
            compiler="vyper", version=compiler_version, optimized=False
        )

        for source_file, contract_info in compilation_artifacts["contracts"].items():
            filename = convert_filename(source_file, _relative_to_short, crytic_compile)
            source_unit = compilation_unit.create_source_unit(filename)
            for contract_name, contract_metadata in contract_info.items():
                source_unit.add_contract_name(contract_name)
                compilation_unit.filename_to_contracts[filename].add(contract_name)

                source_unit.abis[contract_name] = contract_metadata["abi"]
                source_unit.bytecodes_init[contract_name] = contract_metadata["evm"]["bytecode"][
                    "object"
                ].replace("0x", "")
                # Vyper does not provide the source mapping for the init bytecode
                source_unit.srcmaps_init[contract_name] = []
                source_unit.srcmaps_runtime[contract_name] = contract_metadata["evm"][
                    "deployedBytecode"
                ]["sourceMap"].split(";")
                source_unit.bytecodes_runtime[contract_name] = contract_metadata["evm"][
                    "deployedBytecode"
                ]["object"].replace("0x", "")
                source_unit.natspec[contract_name] = Natspec(
                    contract_metadata["userdoc"], contract_metadata["devdoc"]
                )

        for source_file, ast in compilation_artifacts["sources"].items():
            filename = convert_filename(source_file, _relative_to_short, crytic_compile)
            source_unit = compilation_unit.create_source_unit(filename)
            source_unit.ast = ast

    def add_source_files(self, file_paths: List[str]) -> None:
        for file_path in file_paths:
            with open(file_path, "r") as f:
                self.standard_json_input["sources"][file_path] = {
                    "content": f.read(),
                }

    def clean(self, **_kwargs: str) -> None:
        """Clean compilation artifacts

        Args:
            **_kwargs: unused.
        """
        return

    def is_dependency(self, _path: str) -> bool:
        """Check if the path is a dependency (not supported for vyper)

        Args:
            _path (str): path to the target

        Returns:
            bool: True if the target is a dependency
        """
        return False

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """Check if the target is a vyper project

        Args:
            target (str): path to the target
            **kwargs: optional arguments. Used "vyper_ignore"

        Returns:
            bool: True if the target is a vyper project
        """
        vyper_ignore = kwargs.get("vyper_ignore", False)
        if vyper_ignore:
            return False
        return os.path.isfile(target) and target.endswith(".vy")

    def _guessed_tests(self) -> List[str]:
        """Guess the potential unit tests commands

        Returns:
            List[str]: The guessed unit tests commands
        """
        return []


def _run_vyper_standard_json(
    standard_input_path: str,
    vyper: str,
    env: Optional[Dict] = None,
    working_dir: Optional[str] = None,
) -> Dict:
    """Run vyper and write compilation output to a file

    Args:
        standard_input_path (str): path to the standard input json file
        vyper (str): vyper binary
        env (Optional[Dict], optional): Environment variables. Defaults to None.
        working_dir (Optional[str], optional): Working directory. Defaults to None.

    Raises:
        InvalidCompilation: If vyper failed to run

    Returns:
        Dict: Vyper json compilation artifact
    """
    with tempfile.NamedTemporaryFile(mode="a+") as f:
        cmd = [vyper, standard_input_path, "--standard-json", "-o", f.name]
        success = run(cmd, cwd=working_dir, extra_env=env)
        if success is None:
            raise InvalidCompilation("Vyper compilation failed")
        f.seek(0)
        return json.loads(f.read())


def _relative_to_short(relative: Path) -> Path:
    """Translate relative path to short (do nothing for vyper)

    Args:
        relative (Path): path to the target

    Returns:
        Path: Translated path
    """
    return relative
