import os
import json
import logging
import subprocess

from .types import Type
from ..utils.naming import extract_filename, extract_name, combine_filename_name
from .exceptions import InvalidCompilation

logger = logging.getLogger("CryticCompile")


def compile(crytic_compile, target, **kwargs):
    crytic_compile.type = Type.SOLC
    solc = kwargs.get('solc', 'solc')
    solc_disable_warnings = kwargs.get('solc_disable_warnings', False)
    solc_arguments = kwargs.get('solc_arguments', '')
    solc_compact_ast = kwargs.get('solc_compact_ast', True)
    solc_remaps = kwargs.get('solc_remaps', None)

    targets_json = _run_solc(crytic_compile,
                             target,
                             solc,
                             solc_disable_warnings,
                             solc_arguments,
                             solc_compact_ast,
                             solc_remaps=solc_remaps)

    for original_contract_name, info in targets_json["contracts"].items():
        contract_name = extract_name(original_contract_name)
        contract_filename = extract_filename(original_contract_name)
        crytic_compile.contracts_names.add(contract_name)
        crytic_compile.contracts_filenames[contract_name] = contract_filename
        crytic_compile.abis[contract_name] = json.loads(info['abi'])
        crytic_compile.init_bytecodes[contract_name] = info['bin']
        crytic_compile.runtime_bytecodes[contract_name] = info['bin-runtime']
        crytic_compile.srcmaps[contract_name] = info['srcmap'].split(';')
        crytic_compile.srcmaps_runtime[contract_name] = info['srcmap-runtime'].split(';')

    for path, info in targets_json["sources"].items():
        crytic_compile.filenames.add(path)
        crytic_compile.asts[path] = info['AST']

def is_solc(target):
    return os.path.isfile(target) and target.endswith('.sol')

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
                'srcmap': ';'.join(crytic_compile.srcmap(contract_name)),
                'srcmap-runtime': ';'.join(crytic_compile.srcmap_runtime(contract_name)),
                'abi': abi,
                'bin': crytic_compile.init_bytecode(contract_name),
                'bin-runtime': crytic_compile.runtime_bytecode(contract_name)
            }

        sources = {filename : {"AST": ast} for (filename, ast) in crytic_compile.asts.items()}
        sourceList = list(crytic_compile.filenames)

        output = {'sources' : sources,
                  'sourceList' : sourceList,
                  'contracts': contracts}

        json.dump(output, f)


def _run_solc(crytic_compile, filename, solc, solc_disable_warnings, solc_arguments, solc_compact_ast, solc_remaps=None, env=None):
    if not os.path.isfile(filename):
        logger.error('{} does not exist (are you in the correct directory?)'.format(filename))
        exit(-1)

    if not filename.endswith('.sol'):
        raise InvalidCompilation('Incorrect file format')

    options = 'abi,ast,bin,bin-runtime,srcmap,srcmap-runtime,hashes'
    if solc_compact_ast:
        options += ',compact-format'
    cmd = [solc]
    if solc_remaps:
        cmd += solc_remaps
    cmd += [filename, '--combined-json', options]
    if solc_arguments:
        # To parse, we first split the string on each '--'
        solc_args = solc_arguments.split('--')
        # Split each argument on the first space found
        # One solc option may have multiple argument sepparated with ' '
        # For example: --allow-paths /tmp .
        # split() removes the delimiter, so we add it again
        solc_args = [('--' + x).split(' ', 1) for x in solc_args if x]
        # Flat the list of list
        solc_args = [item for sublist in solc_args for item in sublist]
        cmd += solc_args
    # Add . as default allowed path
    if '--allow-paths' not in cmd:
        cmd += ['--allow-paths', '.']

    if env:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    else:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    stdout, stderr = stdout.decode(), stderr.decode()  # convert bytestrings to unicode strings

    if stderr and (not solc_disable_warnings):
        logger.info('Compilation warnings/errors on %s:\n%s', filename, stderr)

    try:
        ret = json.loads(stdout)
        return ret
    except json.decoder.JSONDecodeError:
        raise InvalidCompilation(f'Invalid solc compilation {stderr}')