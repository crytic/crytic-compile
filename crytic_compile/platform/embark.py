import os
import json
import logging
import subprocess

from .types import Type
from .exceptions import InvalidInput
logger = logging.getLogger("CryticCompile")


def compile(crytic_compile, target, embark_ignore_compile, embark_overwrite_config):
    crytic_compile._type = Type.EMBARK
    plugin_name = '@trailofbits/embark-contract-info'
    with open('embark.json') as f:
        embark_json = json.load(f)
    if embark_overwrite_config:
        write_embark_json = False
        if (not 'plugins' in embark_json):
            embark_json['plugins'] = {plugin_name: {'flags': ""}}
            write_embark_json = True
        elif (not plugin_name in embark_json['plugins']):
            embark_json['plugins'][plugin_name] = {'flags': ""}
            write_embark_json = True
        if write_embark_json:
            process = subprocess.Popen(
                ['npm', 'install', 'git://github.com/crytic/embark-contract-info#dev-improve-output'])
            _, stderr = process.communicate()
            with open('embark.json', 'w') as outfile:
                json.dump(embark_json, outfile, indent=2)
    else:
        if (not 'plugins' in embark_json) or (not plugin_name in embark_json['plugins']):
            raise InvalidInput(
                'embark-contract-info plugin was found in embark.json. Please install the plugin (see https://github.com/crytic/crytic-compile/wiki/Usage#embark), or use --embark-overwrite-config.')

    if not embark_ignore_compile:
        process = subprocess.Popen(['embark', 'build', '--contracts'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        logger.info("%s\n" % stdout.decode())
        if stderr:
            # Embark might return information to stderr, but compile without issue
            logger.error("%s" % stderr.decode())
    infile = os.path.join(target, 'crytic-export', 'contracts.json')
    if not os.path.isfile(infile):
        raise InvalidInput(
            'Embark did not generate the AST file. Is Embark installed (npm install -g embark)? Is embark-contract-info installed? (npm install -g embark).')
    with open(infile, 'r') as f:
        targets_loaded = json.load(f)
        crytic_compile._asts = targets_loaded['asts']
        for f in crytic_compile._abis:
            crytic_compile._filenames.add(f)

        for contract_name, info in targets_loaded['contracts'].items():
            crytic_compile.contracts_name.add(contract_name)



            if 'abi' in info:
                crytic_compile.abis[contract_name] = info['abi']
            if 'bin' in info:
                crytic_compile.init_bytecodes[contract_name] = info['bin'].replace('0x', '')
            if 'bin-runtime' in info:
                crytic_compile.runtime_bytecodes[contract_name] = info['bin-runtime'].replace('0x', '')
