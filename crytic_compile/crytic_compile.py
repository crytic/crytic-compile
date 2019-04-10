import os
import subprocess
import json
import logging
import platform
import glob
from enum import Enum

logger = logging.getLogger("CryticCompile")
logging.basicConfig()

class InvalidInput(Exception):
    pass

class Type(Enum):
    SOLC = 1
    TRUFFLE = 2
    EMBARK = 3

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

        self._contracts_name = set()
        self._filenames = set()

        self._type = None

        self._run(target, **kwargs)

    @property
    def contracts_name(self):
        return self._contracts_name

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
            self._export_solc(**kwargs)
        elif export_format == "truffle":
            self._export_truffle(**kwargs)
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
                contracts[contract_name] = {
                    'abi': self.abi(contract_name),
                    'bin': self.init_bytecode(contract_name),
                    'bin-runtime': self.runtime_bytecode(contract_name)
                }

            output = {'asts' : self._asts,
                      'contracts': contracts}

            json.dump(output, f)

    def _export_solc(self, **kwargs):
        export_dir = kwargs.get('export_dir', 'crytic-export')
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
        path = os.path.join(export_dir, "combined_solc.json")

        with open(path, 'w') as f:
            contracts = dict()
            for contract_name in self.contracts_name:
                abi = str(self.abi(contract_name))
                abi = abi.replace('\'', '\"')
                abi = abi.replace('True', 'true')
                abi = abi.replace('False', 'false')
                abi = abi.replace(' ', '')
                contracts[contract_name] = {
                    'srcmap': '',
                    'srcmap-runtime': '',
                    'abi': abi,
                    'bin': self.init_bytecode(contract_name),
                    'bin-runtime': self.runtime_bytecode(contract_name)
                }

            sources = {contract_name : {"AST": ast} for (contract_name, ast) in self._asts.items()}
            sourceList = [contract_name.split(":")[0] for contract_name in self.contracts_name ]

            output = {'sources' : sources,
                      'sourceList' : sourceList,
                      'contracts': contracts}

            json.dump(output, f)

    def _export_truffle(self, **kwargs):
        export_dir = kwargs.get('export_dir', 'crytic-export')
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        for contract_name in self.contracts_name:
            base_name = contract_name[contract_name.rfind(':')+1:]
            filename = contract_name[:contract_name.rfind(':')]
            with open(os.path.join(export_dir, base_name + '.json'), 'w') as f:
                output = {
                    "contractName": base_name,
                    "abi": self.abi(contract_name),
                    "bytecode": "0x" + self.init_bytecode(contract_name),
                    "deployedBytecode": "0x" + self.runtime_bytecode(contract_name),
                    "ast": self.ast(filename)
                }
                json.dump(output, f)


    def _run(self, target, **kwargs):

        truffle_ignore = kwargs.get('truffle_ignore', False)
        embark_ignore = kwargs.get('embark_ignore', False)

        # truffle directory
        if not truffle_ignore and (os.path.isfile(os.path.join(target, 'truffle.js')) or
                                     os.path.isfile(os.path.join(target, 'truffle-config.js'))):
            self._init_from_truffle(target,
                                    kwargs.get('truffle_build_directory', 'build/targets'),
                                    kwargs.get('truffle_ignore_compile', False),
                                    kwargs.get('truffle_version', None))
        # embark directory
        elif not embark_ignore and os.path.isfile(os.path.join(target, 'embark.json')):
            self._init_from_embark(target,
                                   kwargs.get('embark_ignore_compile', False),
                                   kwargs.get('embark_overwrite_config', False))
        # .json or .sol provided
        else:
            self._init_from_solc(target, **kwargs)

    def _init_from_embark(self, target, embark_ignore_compile, embark_overwrite_config):
        self._type = Type.EMBARK
        plugin_name = '@trailofbits/embark-contract-info'
        with open('embark.json') as f:
            embark_json = json.load(f)
        if embark_overwrite_config:
            write_embark_json = False
            if (not 'plugins' in embark_json):
                embark_json['plugins'] = {plugin_name:{'flags':""}}
                write_embark_json = True
            elif (not plugin_name in embark_json['plugins']):
                embark_json['plugins'][plugin_name] = {'flags':""}
                write_embark_json = True
            if write_embark_json:
                process = subprocess.Popen(['npm','install', 'git://github.com/crytic/embark-contract-info#dev-improve-output'])
                _, stderr = process.communicate()
                with open('embark.json', 'w') as outfile:
                    json.dump(embark_json, outfile, indent=2)
        else:
            if (not 'plugins' in embark_json) or (not plugin_name in embark_json['plugins']):
                raise InvalidInput('embark-contract-info plugin was found in embark.json. Please install the plugin (see https://github.com/crytic/crytic-compile/wiki/Usage#embark), or use --embark-overwrite-config.')


        if not embark_ignore_compile:
            process = subprocess.Popen(['embark', 'build', '--contracts'],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            logger.info("%s\n"%stdout.decode())
            if stderr:
                # Embark might return information to stderr, but compile without issue
                logger.error("%s"%stderr.decode())
        infile = os.path.join(target, 'crytic-export', 'contracts.json')
        if not os.path.isfile(infile):
            raise InvalidInput('Embark did not generate the AST file. Is Embark installed (npm install -g embark)? Is embark-contract-info installed? (npm install -g embark).')
        with open(infile, 'r') as f:
            targets_loaded = json.load(f)
            self._asts = targets_loaded['asts']
            for f in self._abis:
                self._filenames.add(f)

            for contract_name, info in targets_loaded['contracts'].items():
                self._contracts_name.add(contract_name)
                if 'abi' in info:
                    self._abis[contract_name] = info['abi']
                if 'bin' in info:
                    self._init_bytecodes[contract_name] = info['bin'].replace('0x', '')
                if 'bin-runtime' in info:
                    self._runtime_bytecodes[contract_name] = info['bin-runtime'].replace('0x', '')


    def _init_from_truffle(self, target, build_directory, truffle_ignore_compile, truffle_version):
        self._type = Type.TRUFFLE
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
            stdout, stderr = stdout.decode(), stderr.decode()# convert bytestrings to unicode strings

            logger.info(stdout)

            if stderr:
                logger.error(stderr)
        if not os.path.isdir(os.path.join(target, build_directory)):
            raise InvalidInput('No truffle build directory found, did you run `truffle compile`?')
        filenames = glob.glob(os.path.join(target, build_directory, '*.json'))

        for filename in filenames:
            with open(filename, encoding='utf8') as f:
                target_loaded = json.load(f)
                self._asts[target_loaded['ast']['absolutePath']] = target_loaded['ast']
                self._filenames.add(target_loaded['ast']['absolutePath'])
                contract_name = target_loaded['ast']['absolutePath'] + ':' + target_loaded['contractName']
                self._contracts_name.add(contract_name)
                self._abis[contract_name] = target_loaded['abi']
                self._init_bytecodes[contract_name] = target_loaded['bytecode'].replace('0x', '')
                self._runtime_bytecodes[contract_name] = target_loaded['deployedBytecode'].replace('0x', '')

    def _init_from_solc(self, target, **kwargs):
        self._type = Type.SOLC
        solc = kwargs.get('solc', 'solc')
        solc_disable_warnings = kwargs.get('solc_disable_warnings', False)
        solc_arguments = kwargs.get('solc_arguments', '')
        solc_compact_ast = kwargs.get('solc_compact_ast', True)

        targets_json = self._run_solc(target,
                                      solc,
                                      solc_disable_warnings,
                                      solc_arguments,
                                      solc_compact_ast)

        for contract_name, info in targets_json["contracts"].items():
            self._contracts_name.add(contract_name)
            self._abis[contract_name] = json.loads(info['abi'])
            self._init_bytecodes[contract_name] = info['bin']
            self._runtime_bytecodes[contract_name] = info['bin-runtime']

        for path, info in targets_json["sources"].items():
            self._filenames.add(path)
            self._asts[path] = info['AST']

    def _run_solc(self, filename, solc, solc_disable_warnings, solc_arguments, solc_compact_ast):
        if not os.path.isfile(filename):
            logger.error('{} does not exist (are you in the correct directory?)'.format(filename))
            exit(-1)

        if not filename.endswith('.sol'):
            raise Exception('Incorrect file format')

        options = 'abi,ast,bin,bin-runtime'
        if solc_compact_ast:
            options += ',compact-format'
        cmd = [solc, filename, '--combined-json', options]
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

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        stdout, stderr = stdout.decode(), stderr.decode()  # convert bytestrings to unicode strings

        if stderr and (not solc_disable_warnings):
            logger.info('Compilation warnings/errors on %s:\n%s', filename, stderr)

        return json.loads(stdout)



