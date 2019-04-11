import os
import json
import logging

from .platform.solc import compile as compile_solc, export as export_solc
from .platform.truffle import compile as compile_truffle, export as export_truffle
from .platform.embark import compile as compile_embark
from .utils.naming import combine_filename_name

logger = logging.getLogger("CryticCompile")
logging.basicConfig()



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

        # cryticcompile store the name and the filename of the contract separately
        # but the exported json follow the format: /path:Contract, to follow standard format
        self._contracts_name = set() # set containing all the contract name
        self._filenames = set() # set containing all the filenames
        self._contracts_filenames = {} # mapping from contract name to filename

        self._type = None

        self._run(target, **kwargs)

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


    def _run(self, target, **kwargs):

        truffle_ignore = kwargs.get('truffle_ignore', False)
        embark_ignore = kwargs.get('embark_ignore', False)

        # truffle directory
        if not truffle_ignore and (os.path.isfile(os.path.join(target, 'truffle.js')) or
                                     os.path.isfile(os.path.join(target, 'truffle-config.js'))):
            compile_truffle(self, target, **kwargs)
        # embark directory
        elif not embark_ignore and os.path.isfile(os.path.join(target, 'embark.json')):
            compile_embark(self, target, **kwargs)
        # .json or .sol provided
        else:
            compile_solc(self, target, **kwargs)








