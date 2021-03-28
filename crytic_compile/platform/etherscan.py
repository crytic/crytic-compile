"""
Etherscan platform.
"""

import json
import logging
import os
import re
import urllib.request
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Union, Tuple

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.solc import _run_solc
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import Filename, convert_filename, extract_filename, extract_name

# Cycle dependency
from crytic_compile.utils.natspec import Natspec

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")

ETHERSCAN_BASE = "https://api%s.etherscan.io/api?module=contract&action=getsourcecode&address=%s"

ETHERSCAN_BASE_BYTECODE = "https://%setherscan.io/address/%s#code"

SUPPORTED_NETWORK = {
    # Key, (prefix_base, perfix_bytecode)
    "mainet:": ("", ""),
    "ropsten:": ("-ropsten", "ropsten."),
    "kovan:": ("-kovan", "kovan."),
    "rinkeby:": ("-rinkeby", "rinkeby."),
    "goerli:": ("-goerli", "goerli."),
    "tobalaba:": ("-tobalaba", "tobalaba."),
}


def _handle_bytecode(crytic_compile: "CryticCompile", target: str, result_b: bytes):
    # There is no direct API to get the bytecode from etherscan
    # The page changes from time to time, we use for now a simple parsing, it will not be robust
    begin = """Search Algorithm">\nSimilar Contracts</button>\n"""
    begin += """<div id="dividcode">\n<pre class=\'wordwrap\' style=\'height: 15pc;\'>0x"""
    result = result_b.decode("utf8")
    # Removing everything before the begin string
    result = result[result.find(begin) + len(begin) :]
    bytecode = result[: result.find("<")]

    contract_name = f"Contract_{target}"

    contract_filename = Filename(absolute="", relative="", short="", used="")

    crytic_compile.contracts_names.add(contract_name)
    crytic_compile.contracts_filenames[contract_name] = contract_filename
    crytic_compile.abis[contract_name] = {}
    crytic_compile.bytecodes_init[contract_name] = bytecode
    crytic_compile.bytecodes_runtime[contract_name] = ""
    crytic_compile.srcmaps_init[contract_name] = []
    crytic_compile.srcmaps_runtime[contract_name] = []

    crytic_compile.compiler_version = CompilerVersion(
        compiler="unknown", version="", optimized=None
    )

    crytic_compile.bytecode_only = True


# def _etherscan_single_file():


def _handle_single_file(
    source_code: str, addr: str, prefix: str, contract_name: str, export_dir: str
) -> str:
    if prefix:
        filename = os.path.join(export_dir, f"{addr}{prefix}-{contract_name}.sol")
    else:
        filename = os.path.join(export_dir, f"{addr}-{contract_name}.sol")

    with open(filename, "w", encoding="utf8") as file_desc:
        file_desc.write(source_code)

    return filename


def _handle_multiple_files(
    dict_source_code: Dict, addr: str, prefix: str, contract_name: str, export_dir: str
) -> Tuple[str, str]:
    if prefix:
        directory = os.path.join(export_dir, f"{addr}{prefix}-{contract_name}")
    else:
        directory = os.path.join(export_dir, f"{addr}-{contract_name}")

    if "sources" in dict_source_code:
        # etherscan might return an object with a sources prop, which contains an object with contract names as keys
        source_codes = dict_source_code["sources"]
    else:
        # or etherscan might return an object with contract names as keys
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


class Etherscan(AbstractPlatform):
    """
    Etherscan platform
    """

    NAME = "Etherscan"
    PROJECT_URL = "https://etherscan.io/"
    TYPE = Type.ETHERSCAN

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

        if target.startswith(tuple(SUPPORTED_NETWORK)):
            prefix: Union[None, str] = SUPPORTED_NETWORK[target[: target.find(":") + 1]][0]
            prefix_bytecode = SUPPORTED_NETWORK[target[: target.find(":") + 1]][1]
            addr = target[target.find(":") + 1 :]
            etherscan_url = ETHERSCAN_BASE % (prefix, addr)
            etherscan_bytecode_url = ETHERSCAN_BASE_BYTECODE % (prefix_bytecode, addr)

        else:
            etherscan_url = ETHERSCAN_BASE % ("", target)
            etherscan_bytecode_url = ETHERSCAN_BASE_BYTECODE % ("", target)
            addr = target
            prefix = None

        only_source = kwargs.get("etherscan_only_source_code", False)
        only_bytecode = kwargs.get("etherscan_only_bytecode", False)

        etherscan_api_key = kwargs.get("etherscan_api_key", None)

        export_dir = kwargs.get("export_dir", "crytic-export")
        export_dir = os.path.join(
            export_dir, kwargs.get("etherscan_export_dir", "etherscan-contracts")
        )

        if etherscan_api_key:
            etherscan_url += f"&apikey={etherscan_api_key}"
            etherscan_bytecode_url += f"&apikey={etherscan_api_key}"

        source_code: str = ""
        result: Dict[str, Union[bool, str, int]] = dict()
        contract_name: str = ""

        if not only_bytecode:
            with urllib.request.urlopen(etherscan_url) as response:
                html = response.read()

            info = json.loads(html)

            if "result" in info and info["result"] == "Max rate limit reached":
                LOGGER.error("Etherscan API rate limit exceeded")
                raise InvalidCompilation("Etherscan api rate limit exceeded")

            if "message" not in info:
                LOGGER.error("Incorrect etherscan request")
                raise InvalidCompilation("Incorrect etherscan request " + etherscan_url)

            if not info["message"].startswith("OK"):
                LOGGER.error("Contract has no public source code")
                raise InvalidCompilation("Contract has no public source code: " + etherscan_url)

            if "result" not in info:
                LOGGER.error("Contract has no public source code")
                raise InvalidCompilation("Contract has no public source code: " + etherscan_url)

            result = info["result"][0]
            # Assert to help mypy
            assert isinstance(result["SourceCode"], str)
            assert isinstance(result["ContractName"], str)
            source_code = result["SourceCode"]
            contract_name = result["ContractName"]

        if source_code == "" and not only_source:
            LOGGER.info("Source code not available, try to fetch the bytecode only")

            req = urllib.request.Request(
                etherscan_bytecode_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req) as response:
                html = response.read()

            _handle_bytecode(crytic_compile, target, html)
            return

        if source_code == "":
            LOGGER.error("Contract has no public source code")
            raise InvalidCompilation("Contract has no public source code: " + etherscan_url)

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

        crytic_compile.compiler_version = CompilerVersion(
            compiler="solc", version=compiler_version, optimized=optimization_used
        )

        working_dir = None
        try:
            # etherscan might return an object with two curly braces, {{ content }}
            dict_source_code = json.loads(source_code[1:-1])
            filename, working_dir = _handle_multiple_files(
                dict_source_code, addr, prefix, contract_name, export_dir
            )
        except JSONDecodeError:
            try:
                # or etherscan might return an object with single curly braces, { content }
                dict_source_code = json.loads(source_code)
                filename, working_dir = _handle_multiple_files(
                    dict_source_code, addr, prefix, contract_name, export_dir
                )
            except JSONDecodeError:
                filename = _handle_single_file(source_code, addr, prefix, contract_name, export_dir)

        targets_json = _run_solc(
            crytic_compile,
            filename,
            solc=solc,
            solc_disable_warnings=False,
            solc_arguments=solc_arguments,
            env=dict(os.environ, SOLC_VERSION=compiler_version),
            working_dir=working_dir,
        )

        for original_contract_name, info in targets_json["contracts"].items():
            contract_name = extract_name(original_contract_name)
            contract_filename = extract_filename(original_contract_name)
            contract_filename = convert_filename(
                contract_filename, _relative_to_short, crytic_compile, working_dir=working_dir
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
                path, _relative_to_short, crytic_compile, working_dir=working_dir
            )
            crytic_compile.filenames.add(path)
            crytic_compile.asts[path.absolute] = info["AST"]

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Check if the target is an etherscan address

        :param target:
        :return:
        """
        etherscan_ignore = kwargs.get("etherscan_ignore", False)
        if etherscan_ignore:
            return False
        if target.startswith(tuple(SUPPORTED_NETWORK)):
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
