import os
import json
import logging
import subprocess
import platform
import glob
from .types import Type
from .exceptions import InvalidCompilation

logger = logging.getLogger("CryticCompile")

def compile(crytic_compile, target, **kwargs):
    build_directory = kwargs.get('truffle_build_directory', os.path.join('build', 'contracts'))
    truffle_ignore_compile = kwargs.get('truffle_ignore_compile', False)
    truffle_version = kwargs.get('truffle_version', None)
    crytic_compile.type = Type.TRUFFLE
    # Truffle on windows has naming conflicts where it will invoke truffle.js directly instead
    # of truffle.cmd (unless in powershell or git bash). The cleanest solution is to explicitly call
    # truffle.cmd. Reference:
    # https://truffleframework.com/docs/truffle/reference/configuration#resolving-naming-conflicts-on-windows
    if not truffle_ignore_compile:
        truffle_base_command = "truffle" if platform.system() != 'Windows' else "truffle.cmd"
        cmd = [truffle_base_command, 'compile']
        if truffle_version:
            cmd = ['npx', truffle_version, 'compile']
        elif os.path.isfile('package.json'):
            with open('package.json') as f:
                package = json.load(f)
                if 'devDependencies' in package:
                    if 'truffle' in package['devDependencies']:
                        version = package['devDependencies']['truffle']
                        if version.startswith('^'):
                            version = version[1:]
                        truffle_version = 'truffle@{}'.format(version)
                        cmd = ['npx', truffle_version, 'compile']
        logger.info("'{}' running (use --truffle-version truffle@x.x.x to use specific version)".format(' '.join(cmd)))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = process.communicate()
        stdout, stderr = stdout.decode(), stderr.decode()  # convert bytestrings to unicode strings

        logger.info(stdout)
        if stderr:
            logger.error(stderr)
    if not os.path.isdir(os.path.join(target, build_directory)):
        raise InvalidCompilation('No truffle build directory found, did you run `truffle compile`?')
    filenames = glob.glob(os.path.join(target, build_directory, '*.json'))

    for filename in filenames:
        with open(filename, encoding='utf8') as f:
            target_loaded = json.load(f)
            crytic_compile.asts[target_loaded['ast']['absolutePath']] = target_loaded['ast']
            crytic_compile.filenames.add(target_loaded['ast']['absolutePath'])
            contract_name = target_loaded['contractName']
            crytic_compile.contracts_filenames[contract_name] = target_loaded['ast']['absolutePath']
            crytic_compile.contracts_names.add(contract_name)
            crytic_compile.abis[contract_name] = target_loaded['abi']
            crytic_compile.bytecodes_init[contract_name] = target_loaded['bytecode'].replace('0x', '')
            crytic_compile.bytecodes_runtime[contract_name] = target_loaded['deployedBytecode'].replace('0x', '')
            crytic_compile.srcmaps_init[contract_name] = target_loaded['sourceMap'].split(';')
            crytic_compile.srcmaps_runtime[contract_name] = target_loaded['deployedSourceMap'].split(';')


def export(crytic_compile, **kwargs):
    export_dir = kwargs.get('export_dir', 'crytic-export')
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    for contract_name in crytic_compile.contracts_names:
        filename = crytic_compile.contracts_filenames[contract_name]
        with open(os.path.join(export_dir, contract_name  + '.json'), 'w') as f:
            output = {
                "contractName": contract_name ,
                "abi": crytic_compile.abi(contract_name),
                "bytecode": "0x" + crytic_compile.bytecode_init(contract_name),
                "deployedBytecode": "0x" + crytic_compile.bytecode_runtime(contract_name),
                "ast": crytic_compile.ast(filename)
            }
            json.dump(output, f)


def is_truffle(target):
    return (os.path.isfile(os.path.join(target, 'truffle.js')) or
     os.path.isfile(os.path.join(target, 'truffle-config.js')))