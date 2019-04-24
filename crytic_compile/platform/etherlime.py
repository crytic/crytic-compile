import os
import json
import logging
import subprocess
import glob
import re
from pathlib import Path
from .types import Type
from .exceptions import InvalidCompilation
from ..utils.naming import convert_filename
from ..compiler.compiler import CompilerVersion
logger = logging.getLogger("CryticCompile")


def compile(crytic_compile, target, **kwargs):

    etherlime_ignore_compile = kwargs.get('etherlime_ignore_compile', False)

    crytic_compile.type = Type.ETHERLIME
    build_directory = "build"

    compile_arguments = kwargs.get('etherlime_compile_arguments', None)

    if not etherlime_ignore_compile:
        cmd = ["etherlime", "compile", target]

        if compile_arguments:
                cmd += compile_arguments.split(' ')

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = process.communicate()
        stdout, stderr = stdout.decode(), stderr.decode()  # convert bytestrings to unicode strings

        logger.info(stdout)

        if stderr:
            logger.error(stderr)

    # similar to truffle
    if not os.path.isdir(os.path.join(target, build_directory)):
        raise InvalidCompilation('No truffle build directory found, did you run `truffle compile`?')
    filenames = glob.glob(os.path.join(target, build_directory, '*.json'))

    version = None
    compiler = "solc-js"

    for filename in filenames:
        with open(filename, encoding='utf8') as f:
            target_loaded = json.load(f)

            if version is None:
                if "compiler" in target_loaded:
                    if "version" in target_loaded["compiler"]:
                        version = re.findall('\d+\.\d+\.\d+', target_loaded["compiler"]["version"])[0]

            filename =target_loaded['ast']['absolutePath']
            filename = convert_filename(filename, _relative_to_short)
            crytic_compile.asts[filename.absolute] = target_loaded['ast']
            crytic_compile.filenames.add(filename)
            contract_name = target_loaded['contractName']
            crytic_compile.contracts_filenames[contract_name] = filename
            crytic_compile.contracts_names.add(contract_name)
            crytic_compile.abis[contract_name] = target_loaded['abi']
            crytic_compile.bytecodes_init[contract_name] = target_loaded['bytecode'].replace('0x', '')
            crytic_compile.bytecodes_runtime[contract_name] = target_loaded['deployedBytecode'].replace('0x', '')
            crytic_compile.srcmaps_init[contract_name] = target_loaded['sourceMap'].split(';')
            crytic_compile.srcmaps_runtime[contract_name] = target_loaded['deployedSourceMap'].split(';')

    crytic_compile.compiler_version = CompilerVersion(compiler=compiler,
                                                      version=version,
                                                      optimized=_is_optimized(compile_arguments ))

def is_etherlime(target):
    if os.path.isfile(os.path.join(target, 'package.json')):
        with open('package.json') as f:
            package = json.load(f)
        if "dependencies" in package:
            return "etherlime" in package["dependencies"]
    return False


def _is_optimized(compile_arguments):
    if compile_arguments:
        return '--run' in compile_arguments
    return False

def _relative_to_short(relative):
    short = relative
    try:
        short = short.relative_to(Path('contracts'))
    except ValueError:
        try:
            short = short.relative_to('node_modules')
        except ValueError:
            pass
    return short