import os
import json
import logging
import glob


import subprocess

from .types import Type
from ..utils.naming import extract_filename, extract_name, combine_filename_name

logger = logging.getLogger("CryticCompile")


def compile(crytic_compile, target, **kwargs):
    crytic_compile.type = Type.DAPP
    dapp_ignore_compile = kwargs.get('dapp_ignore_compile', False)
    dir = os.path.join(target, "out")

    if not dapp_ignore_compile:
        _run_dapp()

    files = glob.glob(dir + '/**/*.sol.json', recursive=True)
    for file in files:
        with open(file) as f:
            targets_json = json.load(f)
        for original_contract_name, info in targets_json["contracts"].items():
            contract_name = extract_name(original_contract_name)
            contract_filename = extract_filename(original_contract_name)
            crytic_compile.contracts_names.add(contract_name)
            crytic_compile.contracts_filenames[contract_name] = contract_filename
            crytic_compile.abis[contract_name] = json.loads(info['abi'])
            crytic_compile.bytecodes_init[contract_name] = info['bin']
            crytic_compile.bytecodes_runtime[contract_name] = info['bin-runtime']
            crytic_compile.srcmaps_init[contract_name] = info['srcmap'].split(';')
            crytic_compile.srcmaps_runtime[contract_name] = info['srcmap-runtime'].split(';')

        for path, info in targets_json["sources"].items():
            crytic_compile.filenames.add(path)
            crytic_compile.asts[path] = info['AST']


def export(crytic_compile, **kwargs):
    export_dir = kwargs.get('export_dir', 'crytic-export')
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    path = os.path.join(export_dir, "combined_solc.json")

    with open(path, 'w') as f:
        contracts = dict()
        for contract_name in crytic_compile.contracts_names:
            abi = str(crytic_compile.abi(contract_name))
            abi = abi.replace('\'', '\"')
            abi = abi.replace('True', 'true')
            abi = abi.replace('False', 'false')
            abi = abi.replace(' ', '')
            exported_name = combine_filename_name(crytic_compile.contracts_filenames[contract_name], contract_name)
            contracts[exported_name] = {
                'srcmap': '',
                'srcmap-runtime': '',
                'abi': abi,
                'bin': crytic_compile.bytecode_init(contract_name),
                'bin-runtime': crytic_compile.bytecode_runtime(contract_name)
            }

        sources = {filename : {"AST": ast} for (filename, ast) in crytic_compile.asts.items()}
        sourceList = crytic_compile.filenames

        output = {'sources' : sources,
                  'sourceList' : sourceList,
                  'contracts': contracts}

        json.dump(output, f)

def is_dapp(target):
    """
    Heuristic used: check if "dapp build" is present in Makefile
    :param target:
    :return:
    """
    makefile = os.path.join(target, "Makefile")
    if os.path.isfile(makefile):
        with open(makefile) as f:
            txt = f.read()
            return "dapp build" in txt
    return False

def _run_dapp():
    cmd = ["dapp", "build"]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, _ = process.communicate()
