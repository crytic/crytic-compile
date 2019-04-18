import os
import json
import logging
import re
import subprocess
import sha3

from .platform.solc import compile as compile_solc, export as export_solc, is_solc
from .platform.truffle import is_truffle, compile as compile_truffle, export as export_truffle
from .platform.embark import is_embark, compile as compile_embark
from .platform.dapp import is_dapp, compile as compile_dapp
from .platform.etherlime import is_etherlime, compile as compile_etherlime
from .platform.etherscan import is_etherscan, compile as compile_etherscan

from .utils.naming import combine_filename_name

logger = logging.getLogger("CryticCompile")
logging.basicConfig()


def is_supported(target):
    supported = [is_solc, is_truffle, is_embark, is_dapp, is_etherlime, is_etherscan]
    return any(f(target) for f in supported)

class CryticCompile:

    def __init__(self, target, **kwargs):
        '''
            Args:
                target (str)
            Keyword Args:
                solc (str): solc binary location (default 'solc')
                solc_disable_warnings (bool): True to disable solc warnings (default false)
                solc_arguments (str): solc arguments (default '')
                solc_compact_ast (bool): ast format (default true)

                truffle_ignore (bool): ignore truffle.js presence (default false)
                truffle_build_directory (str): build truffle directory (default 'build/targets')
                truffle_ignore_compile (bool): do not run truffle compile (default False)
                truffle_version (str): use a specific truffle version (default None)

                embark_ignore (bool): ignore embark.js presence (default false)
                embark_ignore_compile (bool): do not run embark build (default False)
                embark_overwrite_config (bool): overwrite original config file (default false)
        '''
        # ASTS are indexed by path
        self._asts = {}
        # ABI and bytecode are indexed by path:contract_name
        self._abis = {}
        self._runtime_bytecodes = {}
        self._init_bytecodes = {}
        self._hashes = {}

        # cryticcompile store the name and the filename of the contract separately
        # but the exported json follow the format: /path:Contract, to follow standard format
        self._contracts_name = set() # set containing all the contract name
        self._filenames = set() # set containing all the filenames
        self._contracts_filenames = {} # mapping from contract name to filename

        self._type = None

        self._compile(target, **kwargs)

    @property
    def contracts_name(self):
        return self._contracts_name

    @property
    def filenames(self):
        return self._filenames

    @property
    def contracts_filenames(self):
        return self._contracts_filenames

    @property
    def abis(self):
        return self._abis

    @property
    def asts(self):
        return self._asts

    @property
    def runtime_bytecodes(self):
        return self._runtime_bytecodes

    @property
    def init_bytecodes(self):
        return self._init_bytecodes

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, t):
        self._type = t

    def abi(self, name):
        return self._abis.get(name, None)

    def runtime_bytecode(self, name):
        return self._runtime_bytecodes.get(name, None)

    def init_bytecode(self, name):
        return self._init_bytecodes.get(name, None)

    def ast(self, path):
        return self._asts.get(path, None)

    def hashes(self, name):
        if not name in self._hashes:
            self._compute_hashes(name)
        return self._hashes[name]

    def _compute_hashes(self, name):
        self._hashes[name] = {}
        for sig in self.abi(name):
            if 'type' in sig:
                if sig['type'] == 'function':
                    sig_name = sig['name']
                    arguments = ','.join([x['type'] for x in sig['inputs']])
                    sig = f'{sig_name}({arguments})'
                    s = sha3.keccak_256()
                    s.update(sig.encode('utf-8'))
                    self._hashes[name][sig] = int("0x" + s.hexdigest()[:8], 16)


    def export(self, **kwargs):
        """
            Export to json.
            The json format can be crytic-compile, solc or truffle.
            solc format is --combined-json bin-runtime,bin,srcmap,srcmap-runtime,abi,ast,compact-format
            Keyword Args:
                export_format (str): export format (default None). Accepted: None, 'solc', 'truffle'
                export_dir (str): export dir (default crytic-export)
        """
        export_format = kwargs.get('export_format', None)
        if export_format is None or export_format=="crytic-compile":
            self._export_standard(**kwargs)
        elif export_format == "solc":
            export_solc(self, **kwargs)
        elif export_format == "truffle":
            export_truffle(self, **kwargs)
        else:
            raise Exception('Export format unknown')

    def _export_standard(self, **kwargs):
        export_dir = kwargs.get('export_dir', 'crytic-export')
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
        path = os.path.join(export_dir, "contracts.json")

        with open(path, 'w') as f:
            contracts = dict()
            for contract_name in self.contracts_name:
                exported_name = combine_filename_name(self.contracts_filenames[contract_name], contract_name)
                contracts[exported_name] = {
                    'abi': self.abi(contract_name),
                    'bin': self.init_bytecode(contract_name),
                    'bin-runtime': self.runtime_bytecode(contract_name)
                }

            output = {'asts' : self._asts,
                      'contracts': contracts}

            json.dump(output, f)

    def _compile(self, target, **kwargs):

        truffle_ignore = kwargs.get('truffle_ignore', False)
        embark_ignore = kwargs.get('embark_ignore', False)
        dapp_ignore = kwargs.get('dapp_ignore', False)
        etherlime_ignore = kwargs.get('etherlime_ignore', False)
        etherscan_ignore = kwargs.get('etherscan_ignore', False)

        custom_build = kwargs.get('compile_custom_build', False)

        if custom_build:
            truffle_ignore = True
            embark_ignore = True
            dapp_ignore = True
            etherlime_ignore = True
            etherscan_ignore = True

            self._run_custom_build(custom_build)

        compile_force_framework = kwargs.get('compile_force_framework', None)
        if compile_force_framework:
            if compile_force_framework == 'truffle':
                compile_truffle(self, target, **kwargs)
            elif compile_force_framework == 'embark':
                compile_embark(self, target, **kwargs)
            elif compile_force_framework == 'dapp':
                compile_dapp(self, target, **kwargs)
            elif compile_force_framework == 'etherlime':
                compile_etherlime(self, target, **kwargs)
            elif compile_force_framework == 'etherscan':
                compile_etherscan(self, target, **kwargs)
        else:
            # truffle directory
            if not truffle_ignore and is_truffle(target):
                compile_truffle(self, target, **kwargs)
            # embark directory
            elif not embark_ignore and is_embark(target):
                compile_embark(self, target, **kwargs)
            # dap directory
            elif not dapp_ignore and is_dapp(target):
                compile_dapp(self, target, **kwargs)
            #etherlime directory
            elif not etherlime_ignore and is_etherlime(target):
                compile_etherlime(self, target, **kwargs)
            elif not etherscan_ignore and is_etherscan(target):
                compile_etherscan(self, target, **kwargs)
            # .json or .sol provided
            else:
                compile_solc(self, target, **kwargs)

        remove_metadata = kwargs.get('compile_remove_metadata', False)
        if remove_metadata:
            self._remove_metadata()

    def _run_custom_build(self, custom_build):
        cmd = custom_build.split(' ')

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        stdout, stderr = stdout.decode(), stderr.decode()  # convert bytestrings to unicode strings

        logger.info(stdout)
        if stderr:
            logger.error('Custom build error: \n%s', stderr)


    def _remove_metadata(self):
        '''
            Init bytecode contains metadata that needs to be removed
            see http://solidity.readthedocs.io/en/v0.4.24/metadata.html#encoding-of-the-metadata-hash-in-the-bytecode
        '''
        self._init_bytecodes = {key: re.sub(
                    r'a165627a7a72305820.{64}0029',
                    r'',
                    bytecode
                ) for (key, bytecode) in self._init_bytecodes.items()}

        self._runtime_bytecodes = {key: re.sub(
            r'a165627a7a72305820.{64}0029',
            r'',
            bytecode
        ) for (key, bytecode) in self._runtime_bytecodes.items()}