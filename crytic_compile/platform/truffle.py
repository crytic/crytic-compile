import os
import json
import logging
import subprocess
import platform
import glob
from .types import Type
from .exceptions import InvalidInput
logger = logging.getLogger("CryticCompile")


def compile(crytic_compile, target, build_directory, truffle_ignore_compile, truffle_version):
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
        raise InvalidInput('No truffle build directory found, did you run `truffle compile`?')
    filenames = glob.glob(os.path.join(target, build_directory, '*.json'))

    for filename in filenames:
        with open(filename, encoding='utf8') as f:
            target_loaded = json.load(f)
            crytic_compile.asts[target_loaded['ast']['absolutePath']] = target_loaded['ast']
            crytic_compile.filenames.add(target_loaded['ast']['absolutePath'])
            contract_name = target_loaded['contractName']
            crytic_compile.contracts_filenames[contract_name] = target_loaded['ast']['absolutePath']
            crytic_compile.contracts_name.add(contract_name)
            crytic_compile.abis[contract_name] = target_loaded['abi']
            crytic_compile.init_bytecodes[contract_name] = target_loaded['bytecode'].replace('0x', '')
            crytic_compile.runtime_bytecodes[contract_name] = target_loaded['deployedBytecode'].replace('0x', '')


def export(crytic_compile, **kwargs):
    export_dir = kwargs.get('export_dir', 'crytic-export')
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    for contract_name in crytic_compile.contracts_name:
        base_name = contract_name[contract_name.rfind(':') + 1:]
        filename = contract_name[:contract_name.rfind(':')]
        with open(os.path.join(export_dir, base_name + '.json'), 'w') as f:
            output = {
                "contractName": base_name,
                "abi": crytic_compile.abi(contract_name),
                "bytecode": "0x" + crytic_compile.init_bytecode(contract_name),
                "deployedBytecode": "0x" + crytic_compile.runtime_bytecode(contract_name),
                "ast": crytic_compile.ast(filename)
            }
            json.dump(output, f)