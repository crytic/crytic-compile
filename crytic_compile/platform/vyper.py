import subprocess
import os
import re
from pathlib import Path
import json
from .types import Type

from ..compiler.compiler import CompilerVersion
from .exceptions import InvalidCompilation
from ..utils.naming import extract_filename, extract_name, combine_filename_name, convert_filename

def is_vyper(target):
    return os.path.isfile(target) and target.endswith('.vy')

def compile(crytic_compile, target, **kwargs):

    crytic_compile.type = Type.VYPER

    vyper = kwargs.get('vyper', 'vyper')


    targets_json = _run_vyper(target, vyper)

    assert 'version' in targets_json
    crytic_compile.compiler_version = CompilerVersion(compiler="vyper",
                                                      version=targets_json['version'],
                                                      optimized=False)

    assert target in targets_json

    info = targets_json[target]
    contract_filename = convert_filename(target, _relative_to_short)

    contract_name = Path(target).parts[-1]

    crytic_compile.contracts_names.add(contract_name)
    crytic_compile.contracts_filenames[contract_name] = contract_filename
    crytic_compile.abis[contract_name] = info['abi']
    crytic_compile.bytecodes_init[contract_name] = info['bytecode'].replace('0x', '')
    crytic_compile.bytecodes_runtime[contract_name] = info['bytecode_runtime'].replace('0x', '')
    crytic_compile.srcmaps_init[contract_name] = []
    crytic_compile.srcmaps_runtime[contract_name] = []

    crytic_compile.filenames.add(contract_filename)

    ast = _get_vyper_ast(target, vyper)
    crytic_compile.asts[contract_filename.absolute] = ast



def _run_vyper(filename, vyper, env=None, working_dir=None):
    if not os.path.isfile(filename):
        raise InvalidCompilation('{} does not exist (are you in the correct directory?)'.format(filename))

    cmd = [vyper, filename, "-f", "combined_json"]

    additional_kwargs = {'cwd': working_dir} if working_dir else {}
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,  env=env, **additional_kwargs)
    except Exception as e:
        raise InvalidCompilation(e)

    stdout, stderr = process.communicate()

    try:
        res = stdout.split(b'\n')
        res = res[-2]
        return json.loads(res)

    except json.decoder.JSONDecodeError:
        raise InvalidCompilation(f'Invalid vyper compilation\n{stderr}')

def _get_vyper_ast(filename, vyper, env=None, working_dir=None):
    if not os.path.isfile(filename):
        raise InvalidCompilation('{} does not exist (are you in the correct directory?)'.format(filename))

    cmd = [vyper, filename, "-f", "ast"]

    additional_kwargs = {'cwd': working_dir} if working_dir else {}
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,  env=env, **additional_kwargs)
    except Exception as e:
        raise InvalidCompilation(e)

    stdout, stderr = process.communicate()

    try:
        res = stdout.split(b'\n')
        res = res[-2]
        return json.loads(res)

    except json.decoder.JSONDecodeError:
        raise InvalidCompilation(f'Invalid vyper compilation\n{stderr}')



def _relative_to_short(relative):
    return relative

def is_dependency(_path):
    return False
