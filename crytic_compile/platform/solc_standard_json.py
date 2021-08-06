"""
Handle compilation through the standard solc json format
"""
import json
import logging
import os
import subprocess
from typing import TYPE_CHECKING, Dict, List, Optional, Union, Any

from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.solc import Solc, get_version, is_optimized, relative_to_short
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import convert_filename

# Cycle dependency
from crytic_compile.utils.natspec import Natspec

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")


# Inherits is_dependency/is_supported from Solc
class SolcStandardJson(Solc):
    """
    Represent the Standard solc Json object
    """

    NAME = "Solc-json"
    PROJECT_URL = "https://solidity.readthedocs.io/en/latest/using-the-compiler.html#compiler-input-and-output-json-description"
    TYPE = Type.SOLC_STANDARD_JSON

    def __init__(self, target: Union[str, dict] = None, **kwargs: str):
        """Initializes an object which represents solc standard json

        Args:
            target (Union[str, dict], optional): A string path to a standard json, or a standard json. Defaults to None.
            **kwargs: optional arguments.

        Raises:
            ValueError: If invalid json
        """

        super().__init__(str(target), **kwargs)

        if target is None:
            self._json: Dict = dict()
        elif isinstance(target, str):
            if os.path.isfile(target):
                with open(target, mode="r", encoding="utf-8") as target_file:
                    self._json = json.load(target_file)
            else:
                self._json = json.loads(target)

        elif isinstance(target, dict):
            self._json = target
        else:
            raise ValueError("Invalid target for solc standard json input.")

        # Set some default values if they are not provided
        if "language" not in self._json:
            self._json["language"] = "Solidity"
        if "sources" not in self._json:
            self._json["sources"] = {}
        if "settings" not in self._json:
            self._json["settings"] = {}

        if "remappings" not in self._json["settings"]:
            self._json["settings"]["remappings"] = []
        if "optimizer" not in self._json["settings"]:
            self._json["settings"]["optimizer"] = {"enabled": False}
        if "outputSelection" not in self._json["settings"]:
            self._json["settings"]["outputSelection"] = {
                "*": {
                    "*": [
                        "abi",
                        "metadata",
                        "devdoc",
                        "userdoc",
                        "evm.bytecode",
                        "evm.deployedBytecode",
                    ],
                    "": ["ast"],
                }
            }

    def add_source_file(self, file_path: str) -> None:
        """Append file

        Args:
            file_path (str): file to append
        """
        self._json["sources"][file_path] = {"urls": [file_path]}

    def add_remapping(self, remapping: str) -> None:
        """Append our remappings

        Args:
            remapping (str): remapping to add
        """
        self._json["settings"]["remappings"].append(remapping)

    def to_dict(self) -> Dict:
        """Patch in our desired output types

        Returns:
            Dict:
        """
        return self._json

    # pylint: disable=too-many-locals
    def compile(self, crytic_compile: "CryticCompile", **kwargs: Any) -> None:
        """[summary]

        Args:
            crytic_compile (CryticCompile): Associated CryticCompile object
            **kwargs: optional arguments. Used: "solc", "solc_disable_warnings", "solc_args", "solc_working_dir",
                "solc_remaps"
        """

        solc: str = kwargs.get("solc", "solc")
        solc_disable_warnings: bool = kwargs.get("solc_disable_warnings", False)
        solc_arguments: str = kwargs.get("solc_args", "")

        solc_remaps: Optional[Union[str, List[str]]] = kwargs.get("solc_remaps", None)
        solc_working_dir: Optional[str] = kwargs.get("solc_working_dir", None)

        compilation_unit = CompilationUnit(crytic_compile, "standard_json")

        compilation_unit.compiler_version = CompilerVersion(
            compiler="solc",
            version=get_version(solc, None),
            optimized=is_optimized(solc_arguments),
        )

        skip_filename = compilation_unit.compiler_version.version in [
            f"0.4.{x}" for x in range(0, 10)
        ]

        # Add all remappings
        if solc_remaps:
            if isinstance(solc_remaps, str):
                solc_remaps = solc_remaps.split(" ")
            for solc_remap in solc_remaps:
                self.add_remapping(solc_remap)

        # Invoke solc
        targets_json = _run_solc_standard_json(
            self.to_dict(), solc, solc_disable_warnings=solc_disable_warnings
        )

        if "contracts" in targets_json:
            for file_path, file_contracts in targets_json["contracts"].items():
                for contract_name, info in file_contracts.items():
                    # for solc < 0.4.10 we cant retrieve the filename from the ast
                    if skip_filename:
                        contract_filename = convert_filename(
                            self._target,
                            relative_to_short,
                            crytic_compile,
                            working_dir=solc_working_dir,
                        )
                    else:
                        contract_filename = convert_filename(
                            file_path,
                            relative_to_short,
                            crytic_compile,
                            working_dir=solc_working_dir,
                        )
                    compilation_unit.contracts_names.add(contract_name)
                    compilation_unit.contracts_filenames[contract_name] = contract_filename
                    compilation_unit.abis[contract_name] = info["abi"]

                    userdoc = info.get("userdoc", {})
                    devdoc = info.get("devdoc", {})
                    natspec = Natspec(userdoc, devdoc)
                    compilation_unit.natspec[contract_name] = natspec

                    compilation_unit.bytecodes_init[contract_name] = info["evm"]["bytecode"][
                        "object"
                    ]
                    compilation_unit.bytecodes_runtime[contract_name] = info["evm"][
                        "deployedBytecode"
                    ]["object"]
                    compilation_unit.srcmaps_init[contract_name] = info["evm"]["bytecode"][
                        "sourceMap"
                    ].split(";")
                    compilation_unit.srcmaps_runtime[contract_name] = info["evm"][
                        "deployedBytecode"
                    ]["sourceMap"].split(";")

        if "sources" in targets_json:
            for path, info in targets_json["sources"].items():
                if skip_filename:
                    path = convert_filename(
                        self._target,
                        relative_to_short,
                        crytic_compile,
                        working_dir=solc_working_dir,
                    )
                else:
                    path = convert_filename(
                        path, relative_to_short, crytic_compile, working_dir=solc_working_dir
                    )
                crytic_compile.filenames.add(path)
                compilation_unit.filenames.add(path)
                compilation_unit.asts[path.absolute] = info["ast"]

    def _guessed_tests(self) -> List[str]:
        """Guess the potential unit tests commands

        Returns:
            List[str]: The guessed unit tests commands
        """
        return []


# pylint: disable=too-many-locals
def _run_solc_standard_json(
    solc_input: Dict,
    solc: str,
    solc_disable_warnings: bool = False,
    working_dir: Optional[Dict] = None,
) -> Dict:
    """Run the solc standard json compilation.
    Ensure that crytic_compile.compiler_version is set prior calling _run_solc

    Args:
        solc_input (Dict): standard json object
        solc (str): path to the solc binary
        solc_disable_warnings (bool): True to not print the solc warnings. Defaults to False.
        working_dir (Optional[Dict], optional): Working directory to run solc. Defaults to None.

    Raises:
        InvalidCompilation: If the compilation failed

    Returns:
        Dict: Solc json output
    """
    cmd = [solc, "--standard-json", "--allow-paths", "."]
    additional_kwargs: Dict = {"cwd": working_dir} if working_dir else {}

    try:
        with subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **additional_kwargs,
        ) as process:
            stdout_b, stderr_b = process.communicate(json.dumps(solc_input).encode("utf-8"))
            stdout, stderr = (
                stdout_b.decode(),
                stderr_b.decode(),
            )  # convert bytestrings to unicode strings

            solc_json_output = json.loads(stdout)

            # Check for errors and raise them if any exist.
            solc_errors = solc_json_output.get("errors", [])
            if solc_errors:
                solc_error_occurred = False
                solc_exception_str = ""
                for solc_error in solc_errors:
                    if solc_error["severity"] != "warning":
                        solc_error_occurred = True
                    elif solc_disable_warnings:
                        continue
                    solc_exception_str += (
                        f"{solc_error.get('type', 'UnknownExceptionType')}: "
                        f"{solc_error.get('formattedMessage', 'N/A')}\n"
                    )

                if solc_error_occurred:
                    raise InvalidCompilation(solc_exception_str)
                if solc_exception_str:
                    LOGGER.warning(solc_exception_str)

            return solc_json_output

    except OSError as error:
        # pylint: disable=raise-missing-from
        raise InvalidCompilation(error)

    except json.decoder.JSONDecodeError:
        # pylint: disable=raise-missing-from
        raise InvalidCompilation(f"Invalid solc compilation {stderr}")
