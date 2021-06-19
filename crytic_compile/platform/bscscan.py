"""
BscScan platform.
"""

import json
import logging
import os
import re
import urllib.request
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Union, Tuple

from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.solc import (
    _run_solc,
    solc_handle_contracts,
)
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import Filename, convert_filename

# Cycle dependency

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")

BSCSCAN_BASE = "https://%sapi.bscscan.com/api?module=contract&action=getsourcecode&address=%s"

BSCSCAN_BASE_BYTECODE = "https://%sbscscan.com/address/%s#code"

# Reserve this feature for other braches on BSC network
BSC_NETWORK = {
    # Key, (prefix_base, perfix_bytecode)
    "bsc:": ("", ""),
}


def _handle_bytecode_bsc(crytic_compile: "CryticCompile", target: str, result_b: bytes):
    # There is no direct API to get the bytecode from bscscan
    # The page changes from time to time, we use for now a simple parsing, it will not be robust
    begin = """Search Algorithm">\nSimilar Contracts</button>\n"""
    begin += """<div id="dividcode">\n<pre class=\'wordwrap\' style=\'height: 15pc;\'>0x"""
    result = result_b.decode("utf8")
    # Removing everything before the begin string
    result = result[result.find(begin) + len(begin) :]
    bytecode = result[: result.find("<")]

    contract_name = f"Contract_{target}"

    contract_filename = Filename(absolute="", relative="", short="", used="")

    compilation_unit = CompilationUnit(crytic_compile, str(target))

    compilation_unit.contracts_names.add(contract_name)
    compilation_unit.contracts_filenames[contract_name] = contract_filename
    compilation_unit.abis[contract_name] = {}
    compilation_unit.bytecodes_init[contract_name] = bytecode
    compilation_unit.bytecodes_runtime[contract_name] = ""
    compilation_unit.srcmaps_init[contract_name] = []
    compilation_unit.srcmaps_runtime[contract_name] = []

    compilation_unit.compiler_version = CompilerVersion(
        compiler="unknown", version="", optimized=None
    )

    crytic_compile.bytecode_only = True


# def _bscscan_single_file():


def _handle_single_file_bsc(
    source_code: str, addr: str, prefix: str, contract_name: str, export_dir: str
) -> str:
    if prefix:
        filename = os.path.join(export_dir, f"{addr}{prefix}-{contract_name}.sol")
    else:
        filename = os.path.join(export_dir, f"{addr}-{contract_name}.sol")

    with open(filename, "w", encoding="utf8") as file_desc:
        file_desc.write(source_code)

    return filename


def _handle_multiple_files_bsc(
    dict_source_code: Dict, addr: str, prefix: str, contract_name: str, export_dir: str
) -> Tuple[str, str]:
    if prefix:
        directory = os.path.join(export_dir, f"{addr}{prefix}-{contract_name}")
    else:
        directory = os.path.join(export_dir, f"{addr}-{contract_name}")

    if "sources" in dict_source_code:
        # bscscan might return an object with a sources prop, which contains an object with contract names as keys
        source_codes = dict_source_code["sources"]
    else:
        # or bscscan might return an object with contract names as keys
        source_codes = dict_source_code

    returned_filename = None

    for filename, source_code in source_codes.items():
        path_filename = Path(filename)
        if "contracts" in path_filename.parts and not filename.startswith("@"):
            path_filename = Path(*path_filename.parts[path_filename.parts.index("contracts") :])

        # For now we assume that the targeted file is the first one returned
        # This work on the initial tests, but might not be true
        if returned_filename is None:
            returned_filename = path_filename

        path_filename = Path(directory, path_filename)

        if not os.path.exists(path_filename.parent):
            os.makedirs(path_filename.parent)
        with open(path_filename, "w", encoding="utf8") as file_desc:
            file_desc.write(source_code["content"])

    assert returned_filename is not None
    return str(returned_filename), directory


class BscScan(AbstractPlatform):
    """
    BscScan platform
    """

    NAME = "BscScan"
    PROJECT_URL = "https://bscscan.com/"
    TYPE = Type.BSCSCAN

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    def compile(self, crytic_compile: "CryticCompile", **kwargs: str):
        """

        Compile the tharget
        :param crytic_compile:
        :param target:
        :param kwargs:
        :return:
        """

        target = self._target

        solc = kwargs.get("solc", "solc")

        if target.startswith(tuple(BSC_NETWORK)):
            prefix: Union[None, str] = BSC_NETWORK[target[: target.find(":") + 1]][0]
            prefix_bytecode = BSC_NETWORK[target[: target.find(":") + 1]][1]
            addr = target[target.find(":") + 1 :]
            bscscan_url = BSCSCAN_BASE % (prefix, addr)
            bscscan_bytecode_url = BSCSCAN_BASE_BYTECODE % (prefix_bytecode, addr)

        only_source = kwargs.get("bscscan_only_source_code", False)
        only_bytecode = kwargs.get("bscscan_only_bytecode", False)

        bscscan_api_key = kwargs.get("bscscan_api_key", None)

        export_dir = kwargs.get("export_dir", "crytic-export")
        export_dir = os.path.join(
            export_dir, kwargs.get("bscscan_export_dir", "bscscan-contracts")
        )

        if bscscan_api_key:
            bscscan_url += f"&apikey={bscscan_api_key}"
            bscscan_bytecode_url += f"&apikey={bscscan_api_key}"

        source_code: str = ""
        result: Dict[str, Union[bool, str, int]] = dict()
        contract_name: str = ""

        if not only_bytecode:
            with urllib.request.urlopen(bscscan_url) as response:
                html = response.read()

            info = json.loads(html)

            if "result" in info and info["result"] == "Max rate limit reached":
                LOGGER.error("BscScan API rate limit exceeded")
                raise InvalidCompilation("BscScan api rate limit exceeded")

            if "message" not in info:
                LOGGER.error("Incorrect bscscan request")
                raise InvalidCompilation("Incorrect bscscan request " + bscscan_url)

            if not info["message"].startswith("OK"):
                LOGGER.error("Contract has no public source code")
                raise InvalidCompilation("Contract has no public source code: " + bscscan_url)

            if "result" not in info:
                LOGGER.error("Contract has no public source code")
                raise InvalidCompilation("Contract has no public source code: " + bscscan_url)

            result = info["result"][0]
            # Assert to help mypy
            assert isinstance(result["SourceCode"], str)
            assert isinstance(result["ContractName"], str)
            source_code = result["SourceCode"]
            contract_name = result["ContractName"]

        if source_code == "" and not only_source:
            LOGGER.info("Source code not available, try to fetch the bytecode only")

            req = urllib.request.Request(
                bscscan_bytecode_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req) as response:
                html = response.read()

            _handle_bytecode_bsc(crytic_compile, target, html)
            return

        if source_code == "":
            LOGGER.error("Contract has no public source code")
            raise InvalidCompilation("Contract has no public source code: " + bscscan_url)

        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        # Assert to help mypy
        assert isinstance(result["CompilerVersion"], str)

        compiler_version = re.findall(r"\d+\.\d+\.\d+", convert_version(result["CompilerVersion"]))[
            0
        ]

        optimization_used: bool = result["OptimizationUsed"] == "1"

        solc_arguments = None
        if optimization_used:
            optimized_run = int(result["Runs"])
            solc_arguments = f"--optimize --optimize-runs {optimized_run}"

        working_dir = None
        try:
            # bscscan might return an object with two curly braces, {{ content }}
            dict_source_code = json.loads(source_code[1:-1])
            filename, working_dir = _handle_multiple_files_bsc(
                dict_source_code, addr, prefix, contract_name, export_dir
            )
        except JSONDecodeError:
            try:
                # or bscscan might return an object with single curly braces, { content }
                dict_source_code = json.loads(source_code)
                filename, working_dir = _handle_multiple_files_bsc(
                    dict_source_code, addr, prefix, contract_name, export_dir
                )
            except JSONDecodeError:
                filename = _handle_single_file_bsc(source_code, addr, prefix, contract_name, export_dir)

        compilation_unit = CompilationUnit(crytic_compile, str(filename))

        targets_json = _run_solc(
            compilation_unit,
            filename,
            solc=solc,
            solc_disable_warnings=False,
            solc_arguments=solc_arguments,
            env=dict(os.environ, SOLC_VERSION=compiler_version),
            working_dir=working_dir,
        )

        compilation_unit.compiler_version = CompilerVersion(
            compiler="solc", version=compiler_version, optimized=optimization_used
        )

        solc_handle_contracts(targets_json, False, compilation_unit, "", working_dir)

        for path, info in targets_json["sources"].items():
            path = convert_filename(
                path, _relative_to_short, crytic_compile, working_dir=working_dir
            )
            crytic_compile.filenames.add(path)
            compilation_unit.asts[path.absolute] = info["AST"]

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Check if the target is an bscscan address

        :param target:
        :return:
        """
        bscscan_ignore = kwargs.get("bscscan_ignore", False)
        if bscscan_ignore:
            return False
        if target.startswith(tuple(BSC_NETWORK)):
            target = target[target.find(":") + 1 :]
        return bool(re.match(r"^\s*0x[a-zA-Z0-9]{40}\s*$", target))

    def is_dependency(self, _path: str) -> bool:
        """
        Always return false

        :param _path:
        :return:
        """
        return False

    def _guessed_tests(self) -> List[str]:
        """
        Guess the potential unit tests commands

        :return:
        """
        return []


def convert_version(version: str) -> str:
    """
    Convert the compiler version
    :param version:
    :return:
    """
    return version[1 : version.find("+")]


def _relative_to_short(relative: Path) -> Path:
    return relative
