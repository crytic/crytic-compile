"""
Handle compilation through the standard solc json format
"""
import json
import logging
import os
import subprocess
from typing import Union, Dict, List, TYPE_CHECKING, Optional

from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.solc import (
    export as export_solc,
    is_dependency as is_dependency_solc,
    get_version,
    _is_optimized,
    _relative_to_short,
)
from crytic_compile.platform.types import Type
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.utils.naming import convert_filename

# Cycle dependency
if TYPE_CHECKING:
    from crytic_compile import CryticCompile


class SolcStandardJson:
    """
    Represent the Standard solc Json object
    """

    def __init__(self, target: Union[str, dict, "SolcStandardJson"] = None):
        """
        Initializes an object which represents solc standard json
        :param target: A string path to a standard json
        """
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
        elif isinstance(target, SolcStandardJson):
            self._json = target._json
        else:
            raise ValueError(f"Invalid target for solc standard json input.")

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
                "*": {"*": ["abi", "metadata", "evm.bytecode", "evm.deployedBytecode"], "": ["ast"]}
            }

    def add_source_file(self, file_path: str):
        """
        Append file
        :param file_path:
        :return:
        """
        self._json["sources"][file_path] = {"urls": [file_path]}

    def add_remapping(self, remapping: str):
        """
        Append our remappings
        :param remapping:
        :return:
        """
        self._json["settings"]["remappings"].append(remapping)

    def to_dict(self) -> Dict:
        """
        Patch in our desired output types
        :return:
        """
        return self._json


LOGGER = logging.getLogger("CryticCompile")


def compile(
    crytic_compile: "CryticCompile", target: Union[str, dict, "SolcStandardJson"], **kwargs: str
):
    """
    Compile the target
    :param crytic_compile:
    :param target:
    :param kwargs:
    :return:
    """
    crytic_compile.type = Type.SOLC_STANDARD_JSON
    solc = kwargs.get("solc", "solc")
    solc_disable_warnings = kwargs.get("solc_disable_warnings", False)
    solc_arguments = kwargs.get("solc_args", "")
    solc_remaps: Optional[Union[str, List[str]]] = kwargs.get("solc_remaps", None)
    solc_working_dir = kwargs.get("solc_working_dir", None)

    crytic_compile.compiler_version = CompilerVersion(
        compiler="solc", version=get_version(solc), optimized=_is_optimized(solc_arguments)
    )

    skip_filename = crytic_compile.compiler_version.version in [f"0.4.{x}" for x in range(0, 10)]

    # Initialize our solc input
    target = SolcStandardJson(target)

    # Add all remappings
    if solc_remaps:
        if isinstance(solc_remaps, str):
            solc_remaps = solc_remaps.split(" ")
        for solc_remap in solc_remaps:
            target.add_remapping(solc_remap)

    # Invoke solc
    targets_json = _run_solc_standard_json(
        target.to_dict(), solc, solc_disable_warnings=solc_disable_warnings
    )

    if "contracts" in targets_json:
        for file_path, file_contracts in targets_json["contracts"].items():
            for contract_name, info in file_contracts.items():
                # for solc < 0.4.10 we cant retrieve the filename from the ast
                if skip_filename:
                    # TODO investigate the mypy type issue
                    contract_filename = convert_filename(
                        target, _relative_to_short, crytic_compile, working_dir=solc_working_dir
                    )
                else:
                    contract_filename = convert_filename(
                        file_path, _relative_to_short, crytic_compile, working_dir=solc_working_dir
                    )
                crytic_compile.contracts_names.add(contract_name)
                crytic_compile.contracts_filenames[contract_name] = contract_filename
                crytic_compile.abis[contract_name] = info["abi"]
                crytic_compile.bytecodes_init[contract_name] = info["evm"]["bytecode"]["object"]
                crytic_compile.bytecodes_runtime[contract_name] = info["evm"]["deployedBytecode"][
                    "object"
                ]
                crytic_compile.srcmaps_init[contract_name] = info["evm"]["bytecode"][
                    "sourceMap"
                ].split(";")
                crytic_compile.srcmaps_runtime[contract_name] = info["evm"]["deployedBytecode"][
                    "sourceMap"
                ].split(";")

    if "sources" in targets_json:
        for path, info in targets_json["sources"].items():
            if skip_filename:
                path = convert_filename(
                    target, _relative_to_short, crytic_compile, working_dir=solc_working_dir
                )
            else:
                path = convert_filename(
                    path, _relative_to_short, crytic_compile, working_dir=solc_working_dir
                )
            crytic_compile.filenames.add(path)
            crytic_compile.asts[path.absolute] = info["ast"]


def is_solc(target: str):
    """
    Check if the target is a Solidity file
    :param target:
    :return:
    """
    return os.path.isfile(target) and target.endswith(".sol")


def is_dependency(path: str):
    """
    Check if the file is a dependency
    :param path:
    :return:
    """
    return is_dependency_solc(path)


def export(crytic_compile: "CryticCompile", **kwargs: str):
    """
    Export to the standard solc output
    :param crytic_compile:
    :param kwargs:
    :return:
    """
    return export_solc(crytic_compile, **vars(kwargs))


def _run_solc_standard_json(
    solc_input: Dict, solc: str, solc_disable_warnings=False, working_dir=None
):
    """
    Note: Ensure that crytic_compile.compiler_version is set prior calling _run_solc
    :param solc_input:
    :param solc:
    :param solc_disable_warnings:
    :param working_dir:
    :return:
    """
    cmd = [solc, "--standard-json", "--allow-paths", "."]
    additional_kwargs = {"cwd": working_dir} if working_dir else {}

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **additional_kwargs,
    )
    stdout, stderr = process.communicate(json.dumps(solc_input).encode("utf-8"))
    stdout, stderr = (stdout.decode(), stderr.decode())  # convert bytestrings to unicode strings

    try:
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
    except json.decoder.JSONDecodeError:
        raise InvalidCompilation(f"Invalid solc compilation {stderr}")
