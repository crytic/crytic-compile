import json
import logging
import urllib.request
import os
import re

from .types import Type
from .exceptions import  InvalidCompilation
from .solc import _run_solc
from ..utils.naming import extract_filename, extract_name, convert_filename

logger = logging.getLogger("CryticCompile")

ethercan_base = "https://api%s.etherscan.io/api?module=contract&action=getsourcecode&address=%s"

supported_network = {
    "mainet:" : "",
    "ropsten:" : "-ropsten",
    "kovan:" : "-kovan",
    "rinkeby:": "-rinkeby",
    "goerli:": "-goerli",
    "tobalaba:": "-tobalaba"
}

def compile(crytic_compile, target, **kwargs):
    crytic_compile.type = Type.ETHERSCAN

    solc = kwargs.get('solc', 'solc')

    if target.startswith(tuple(supported_network)):
        prefix = supported_network[target[:target.find(':')+1]]
        addr = target[target.find(':')+1:]
        etherscan_url = ethercan_base % (prefix, addr)
    else:
        etherscan_url = ethercan_base % ('', target)

    with urllib.request.urlopen(etherscan_url) as response:
        html = response.read()

    info = json.loads(html)

    if not 'message' in info :
        logger.error('Incorrect etherscan request')
        raise InvalidCompilation('Incorrect etherscan request ' + etherscan_url)

    if info['message'] != 'OK':
        logger.error('Contract has no public source code')
        raise InvalidCompilation('Contract has no public source code: ' + etherscan_url)

    if not 'result' in info:
        logger.error('Contract has no public source code')
        raise InvalidCompilation('Contract has no public source code: ' + etherscan_url)

    result = info['result'][0]
    source_code = result['SourceCode']
    contract_name = result['ContractName']

    filename = os.path.join('crytic-export', contract_name + '.sol')

    if not os.path.exists('crytic-export'):
        os.makedirs('crytic-export')

    with open(filename, 'w') as f:
        f.write(source_code)

    compiler_version = convert_version(result['CompilerVersion'])

    optimizaiton_used = True if result['OptimizationUsed'] == '1' else False
    optimized_run = result['Runs']

    solc_arguments = None
    if optimizaiton_used:
        optimized_run = int(optimized_run)
        solc_arguments = f'--optimize --optimize-runs {optimized_run}'

    solc_compact_ast = True


    if compiler_version in [f'0.4.{x}' for x in range(0, 12)] or\
        compiler_version.startswith('0.3'):
        solc_compact_ast = False

    targets_json = _run_solc(crytic_compile,
                             filename,
                             solc=solc,
                             solc_disable_warnings=False,
                             solc_arguments=solc_arguments,
                             solc_compact_ast=solc_compact_ast,
                             env=dict(os.environ, SOLC_VERSION=compiler_version))

    for original_contract_name, info in targets_json["contracts"].items():
        contract_name = extract_name(original_contract_name)
        contract_filename = extract_filename(original_contract_name)
        contract_filename = convert_filename(contract_filename)
        crytic_compile.contracts_names.add(contract_name)
        crytic_compile.contracts_filenames[contract_name] = contract_filename
        crytic_compile.abis[contract_name] = json.loads(info['abi'])
        crytic_compile.bytecodes_init[contract_name] = info['bin']
        crytic_compile.bytecodes_runtime[contract_name] = info['bin-runtime']
        crytic_compile.srcmaps_init[contract_name] = info['srcmap'].split(';')
        crytic_compile.srcmaps_runtime[contract_name] = info['srcmap-runtime'].split(';')

    for path, info in targets_json["sources"].items():
        path = convert_filename(path)
        crytic_compile.filenames.add(path.absolute)
        crytic_compile.asts[path.absolute] = info['AST']


def is_etherscan(target):
    if target.startswith(tuple(supported_network)):
        target = target[target.find(':') + 1:]
    return re.match('0x[a-zA-Z0-9]{40}', target)


def convert_version(version):
    return version[1:version.find('+')]
