import os
import json
import logging
import subprocess

from ..utils.naming import extract_filename, extract_name

from .types import Type
from .exceptions import InvalidCompilation
logger = logging.getLogger("CryticCompile")


def compile(crytic_compile, target, **kwargs):
    embark_ignore_compile = kwargs.get('embark_ignore_compile', False)
    embark_overwrite_config = kwargs.get('embark_overwrite_config', False)
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
            raise InvalidCompilation(
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
        raise InvalidCompilation(
            'Embark did not generate the AST file. Is Embark installed (npm install -g embark)? Is embark-contract-info installed? (npm install -g embark).')
    with open(infile, 'r') as f:
        targets_loaded = json.load(f)
        crytic_compile._asts = targets_loaded['asts']
        for f in crytic_compile._abis:
            crytic_compile._filenames.add(f)

        for original_contract_name, info in targets_loaded['contracts'].items():
            contract_name = extract_name(original_contract_name)
            contract_filename = extract_filename(original_contract_name)
            crytic_compile.contracts_filenames[contract_name] = contract_filename
            crytic_compile.contracts_names.add(contract_name)


            if 'abi' in info:
                crytic_compile.abis[contract_name] = info['abi']
            if 'bin' in info:
                crytic_compile.init_bytecodes[contract_name] = info['bin'].replace('0x', '')
            if 'bin-runtime' in info:
                crytic_compile.runtime_bytecodes[contract_name] = info['bin-runtime'].replace('0x', '')
            if 'srcmap' in info:
                crytic_compile.srcmaps[contract_name] = info['srcmap'].split(';')
            if 'srcmap-runtime' in info:
                crytic_compile.srcmaps_runtime[contract_name] = info['srcmap-runtime'].split(';')

def is_embark(target):
    return os.path.isfile(os.path.join(target, 'embark.json'))