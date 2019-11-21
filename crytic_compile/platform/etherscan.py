import json
import logging
import urllib.request
import os
import re

from .types import Type
from .exceptions import InvalidCompilation
from .solc import _run_solc
from ..utils.naming import extract_filename, extract_name, convert_filename, Filename
from ..compiler.compiler import CompilerVersion

logger = logging.getLogger("CryticCompile")

ethercan_base = (
    "https://api%s.etherscan.io/api?module=contract&action=getsourcecode&address=%s"
)

ethercan_base_bytecode = (
    "https://%setherscan.io/address/%s#code"
)

supported_network = {
    # Key, (prefix_base, perfix_bytecode)
    "mainet:":   ("",          ""),
    "ropsten:":  ("-ropsten",  "ropsten."),
    "kovan:":    ("-kovan",    "kovan."),
    "rinkeby:":  ("-rinkeby",  "rinkeby."),
    "goerli:":   ("-goerli",   "goerli."),
    "tobalaba:": ("-tobalaba", "tobalaba."),
}


def _handle_bytecode(crytic_compile, target, result):
    # There is no direct API to get the bytecode from etherscan
    # The page changes from time to time, we use for now a simple parsing, it will not be robust
    begin = '''Search Algorithm">\nSimilar Contracts</button>\n<div id="dividcode">\n<pre class=\'wordwrap\' style=\'height: 15pc;\'>0x'''
    result = result.decode('utf8')
    # Removing everything before the begin string
    result = result[result.find(begin)+len(begin):]
    bytecode = result[:result.find('<')]

    contract_name = f'Contract_{target}'

    contract_filename = Filename(
        absolute='',
        relative='',
        short='',
        used='',
    )

    crytic_compile.contracts_names.add(contract_name)
    crytic_compile.contracts_filenames[contract_name] = contract_filename
    crytic_compile.abis[contract_name] = {}
    crytic_compile.bytecodes_init[contract_name] = bytecode
    crytic_compile.bytecodes_runtime[contract_name] = ''
    crytic_compile.srcmaps_init[contract_name] = []
    crytic_compile.srcmaps_runtime[contract_name] = []

    crytic_compile.compiler_version = CompilerVersion(
        compiler="unknown", version='', optimized=None
    )

    crytic_compile.bytecode_only = True

def compile(crytic_compile, target, **kwargs):
    crytic_compile.type = Type.ETHERSCAN

    solc = kwargs.get("solc", "solc")

    if target.startswith(tuple(supported_network)):
        prefix = supported_network[target[: target.find(":") + 1]][0]
        prefix_bytecode = supported_network[target[: target.find(":") + 1]][1]
        addr = target[target.find(":") + 1 :]
        etherscan_url = ethercan_base % (prefix, addr)
        etherscan_bytecode_url = ethercan_base_bytecode % (prefix_bytecode, addr)

    else:
        etherscan_url = ethercan_base % ("", target)
        etherscan_bytecode_url = ethercan_base_bytecode % ("", target)
        addr = target
        prefix = None

    only_source = kwargs.get('etherscan_only_source_code', False)
    only_bytecode = kwargs.get('etherscan_only_bytecode', False)

    source_code = ''
    result = None
    contract_name = None

    if not only_bytecode:
        with urllib.request.urlopen(etherscan_url) as response:
            html = response.read()

        info = json.loads(html)

        if not "message" in info:
            logger.error("Incorrect etherscan request")
            raise InvalidCompilation("Incorrect etherscan request " + etherscan_url)

        if info["message"] != "OK":
            logger.error("Contract has no public source code")
            raise InvalidCompilation("Contract has no public source code: " + etherscan_url)

        if not "result" in info:
            logger.error("Contract has no public source code")
            raise InvalidCompilation("Contract has no public source code: " + etherscan_url)

        result = info["result"][0]
        source_code = result["SourceCode"]
        contract_name = result["ContractName"]

    if source_code == '' and not only_source:
        logger.info('Source code not available, try to fetch the bytecode only')

        req = urllib.request.Request(etherscan_bytecode_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            html = response.read()

        _handle_bytecode(crytic_compile, target, html)
        return


    if prefix:
        filename = os.path.join(
            "crytic-export",
            "etherscan_contracts",
            f"{addr}{prefix}-{contract_name}.sol",
        )
    else:
        filename = os.path.join(
            "crytic-export", "etherscan_contracts", f"{addr}-{contract_name}.sol"
        )

    if not os.path.exists("crytic-export"):
        os.makedirs("crytic-export")

    if not os.path.exists(os.path.join("crytic-export", "etherscan_contracts")):
        os.makedirs(os.path.join("crytic-export", "etherscan_contracts"))

    with open(filename, "w", encoding="utf8") as f:
        f.write(source_code)

    compiler_version = re.findall(
        "\d+\.\d+\.\d+", convert_version(result["CompilerVersion"])
    )[0]

    optimization_used = True if result["OptimizationUsed"] == "1" else False
    optimized_run = result["Runs"]

    solc_arguments = None
    if optimization_used:
        optimized_run = int(optimized_run)
        solc_arguments = f"--optimize --optimize-runs {optimized_run}"

    crytic_compile.compiler_version = CompilerVersion(
        compiler="solc", version=compiler_version, optimized=optimization_used
    )

    targets_json = _run_solc(
        crytic_compile,
        filename,
        solc=solc,
        solc_disable_warnings=False,
        solc_arguments=solc_arguments,
        env=dict(os.environ, SOLC_VERSION=compiler_version),
    )

    for original_contract_name, info in targets_json["contracts"].items():
        contract_name = extract_name(original_contract_name)
        contract_filename = extract_filename(original_contract_name)
        contract_filename = convert_filename(
            contract_filename, _relative_to_short, crytic_compile
        )
        crytic_compile.contracts_names.add(contract_name)
        crytic_compile.contracts_filenames[contract_name] = contract_filename
        crytic_compile.abis[contract_name] = json.loads(info["abi"])
        crytic_compile.bytecodes_init[contract_name] = info["bin"]
        crytic_compile.bytecodes_runtime[contract_name] = info["bin-runtime"]
        crytic_compile.srcmaps_init[contract_name] = info["srcmap"].split(";")
        crytic_compile.srcmaps_runtime[contract_name] = info["srcmap-runtime"].split(
            ";"
        )

    for path, info in targets_json["sources"].items():
        path = convert_filename(path, _relative_to_short, crytic_compile)
        crytic_compile.filenames.add(path)
        crytic_compile.asts[path.absolute] = info["AST"]


def is_etherscan(target):
    if target.startswith(tuple(supported_network)):
        target = target[target.find(":") + 1 :]
    return re.match("^\s*0x[a-zA-Z0-9]{40}\s*$", target)


def is_dependency(_path):
    return False


def convert_version(version):
    return version[1 : version.find("+")]


def _relative_to_short(relative):
    return relative
