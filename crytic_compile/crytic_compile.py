import copy
import os
import json
import glob
import logging
import re
import subprocess
import sha3
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.utils.naming import Filename
from pathlib import Path

from .platform import solc, truffle, embark, dapp, etherlime, etherscan, archive

from .utils.naming import combine_filename_name

logger = logging.getLogger("CryticCompile")
logging.basicConfig()


def is_supported(target):
    supported = [solc.is_solc,
                 truffle.is_truffle,
                 embark.is_embark,
                 dapp.is_dapp,
                 etherlime.is_etherlime,
                 etherscan.is_etherscan,
                 is_archive]
    return any(f(target) for f in supported)


def is_archive(target):
    return os.path.isfile(target) and target.endswith('.ccarchive')


class CryticCompile:

    def __init__(self, target, **kwargs):
        '''
            Args:
                target (str | tuple(export_dict, index))
            Keyword Args:
                See https://github.com/crytic/crytic-compile/wiki/Configuration
        '''
        # ASTS are indexed by absolute path
        self._asts = {}

        # ABI, bytecode and srcmap are indexed by contract_name
        self._abis = {}
        self._runtime_bytecodes = {}
        self._init_bytecodes = {}
        self._hashes = {}
        self._srcmaps = {}
        self._srcmaps_runtime = {}
        self._src_content = {}

        # set containing all the contract names
        self._contracts_name = set()
        # set containing all the contract name without the libraries
        self._contracts_name_without_libraries = None

        # set containing all the filenames (absolute paths)
        self._filenames = set()
        # mapping from contract name to filename (naming.Filename)
        self._contracts_filenames = {}

        # mapping from contract_name to libraries_names (libraries used by the contract)
        self._libraries = {}

        # platform.type
        self._type = None
        self._platform = None

        # compiler.compiler
        self._compiler_version = None

        self._working_dir = Path.cwd()

        # If its a exported archive, we use compilation index 0.
        if isinstance(target, dict):
            target = (target, 0)

        # If its an indexed compilation in the exported archive.
        if isinstance(target, tuple) and len(target) == 2 and \
                isinstance(target[0], dict) and isinstance(target[1], int):
            self._import_archive_compilation(target[0], target[1])
        else:
            self._compile(target, **kwargs)

    ###################################################################################
    ###################################################################################
    # region Filenames
    ###################################################################################
    ###################################################################################


    @property
    def filenames(self):
        """
        :return: list(naming.Filename)
        """
        return self._filenames

    @property
    def contracts_filenames(self):
        """
        Return a dict contract_name -> Filename namedtuple (absolute, used)
        :return: dict(name -> utils.namings.Filename)
        """
        return self._contracts_filenames

    @property
    def contracts_absolute_filenames(self):
        """
        Return a dict (contract_name -> absolute filename)
        :return:
        """
        return {k: f.absolute for (k,f) in self._contracts_filenames.items()}

    def filename_of_contract(self, name):
        """
        :return: utils.namings.Filename
         """
        return self._contracts_filenames[name]

    def absolute_filename_of_contract(self, name):
        """
        :return: Absolute filename
         """
        return self._contracts_filenames[name].absolute

    def used_filename_of_contract(self, name):
        """
        :return: Used filename
         """
        return self._contracts_filenames[name].used

    def find_absolute_filename_from_used_filename(self, used_filename):
        """
        Return the absolute filename based on the used one
        :param used_filename:
        :return: absolute filename
        """
        # Note: we could memoize this function if the third party end up using it heavily
        # If used_filename is already an absolute pathn no need to lookup
        if used_filename in self._filenames:
            return used_filename
        d = {f.used: f.absolute for _, f in self._contracts_filenames}
        if not used_filename in d:
            raise ValueError('f{filename} does not exist in {d}')
        return d[used_filename]

    def relative_filename_from_absolute_filename(self, absolute_filename):
        d = {f.absolute: f.relative for _, f in self._contracts_filenames}
        if not absolute_filename in d:
            raise ValueError('f{absolute_filename} does not exist in {d}')
        return d[absolute_filename]

    def filename_lookup(self, filename):
        """
        Return a crytic_compile.naming.Filename from a any filename form (used/absolute/relative)
        :param filename: str
        :return: crytic_compile.naming.Filename
        """
        d = {}
        for f in self._filenames:
            d[f.absolute] = f
            d[f.relative] = f
            d[f.used] = f
        if not filename in d:
            raise ValueError(f'{filename} does not exist in {d}')
        return d[filename]

    def is_dependency(self, filename):
        return self._platform.is_dependency(filename)

    # endregion
    ###################################################################################
    ###################################################################################
    # region Contract Names
    ###################################################################################
    ###################################################################################

    @property
    def contracts_names(self):
        return self._contracts_name

    @property
    def contracts_names_without_libraries(self):
        if self._contracts_name_without_libraries is None:
            libraries = []
            for c in self._contracts_name:
                libraries += self.libraries_names(c)
            libraries = set(libraries)
            self._contracts_name_without_libraries = set([l for l in self._contracts_name if not l in libraries])
        return self._contracts_name_without_libraries

    # endregion
    ###################################################################################
    ###################################################################################
    # region ABI
    ###################################################################################
    ###################################################################################

    @property
    def abis(self):
        return self._abis

    def abi(self, name):
        return self._abis.get(name, None)

    # endregion
    ###################################################################################
    ###################################################################################
    # region AST
    ###################################################################################
    ###################################################################################

    @property
    def asts(self):
        """

        :return: dict (absolute filename -> AST)
        """
        return self._asts

    def ast(self, path):
        if path not in self._asts:
            try:
                path = self.find_absolute_filename_from_used_filename(path)
            except ValueError:
                pass
        return self._asts.get(path, None)

    # endregion
    ###################################################################################
    ###################################################################################
    # region Bytecode
    ###################################################################################
    ###################################################################################


    @property
    def bytecodes_runtime(self):
        return self._runtime_bytecodes

    @property
    def bytecodes_init(self):
        return self._init_bytecodes


    def bytecode_runtime(self, name, libraries=None):
        runtime = self._runtime_bytecodes.get(name, None)
        return self._update_bytecode_with_libraries(runtime, libraries)

    def bytecode_init(self, name, libraries=None):
        init = self._init_bytecodes.get(name, None)
        return self._update_bytecode_with_libraries(init, libraries)


    # endregion
    ###################################################################################
    ###################################################################################
    # region Source mapping
    ###################################################################################
    ###################################################################################


    @property
    def srcmaps_init(self):
        return self._srcmaps

    @property
    def srcmaps_runtime(self):
        return self._srcmaps_runtime

    def srcmap_init(self, name):
        return self._srcmaps.get(name, [])

    def srcmap_runtime(self, name):
        return self._srcmaps_runtime.get(name, [])

    @property
    def src_content(self):
        # If we have no source code loaded yet, load it for every contract.
        if not self._src_content:
            for name in self.contracts_names:
                filename = self.filename_of_contract(name)
                if filename.absolute not in self._src_content and os.path.isfile(filename.absolute):
                    with open(filename.absolute, encoding='utf8', newline='') as source_file:
                        self._src_content[filename.absolute] = source_file.read()
        return self._src_content

    # endregion
    ###################################################################################
    ###################################################################################
    # region Type
    ###################################################################################
    ###################################################################################


    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, t):
        self._type = t


    # endregion
    ###################################################################################
    ###################################################################################
    # region Compiler information
    ###################################################################################
    ###################################################################################


    @property
    def compiler_version(self):
        """
        Return the compiler used as a namedtuple(compiler, version)
        :return:
        """
        return self._compiler_version

    @compiler_version.setter
    def compiler_version(self, c):
        self._compiler_version = c

    # endregion
    ###################################################################################
    ###################################################################################
    # region Libraries
    ###################################################################################
    ###################################################################################

    def _convert_libraries_names(self, libraries):
        """
        :param libraries: list(name, addr). Name can be the library name, or filename:library_name
        :return:
        """
        new_names = {}
        for (lib, addr) in libraries.items():
            # Prior solidity 0.5
            # libraries were on the format __filename:contract_name_____
            # From solidity 0.5,
            # libraries are on the format __$kecckack(filename:contract_name)[34]$__
            # https://solidity.readthedocs.io/en/v0.5.7/050-breaking-changes.html#command-line-and-json-interfaces

            lib_4 = '__' + lib + '_'* (38-len(lib))

            s = sha3.keccak_256()
            s.update(lib.encode('utf-8'))
            lib_5 = "__$" + s.hexdigest()[:34] + "$__"

            new_names[lib] = addr
            new_names[lib_4] = addr
            new_names[lib_5] = addr

            if lib in self.contracts_names:
                lib_filename = self.contracts_filenames[lib]

                lib_with_abs_filename = lib_filename.absolute + ':' + lib
                lib_with_abs_filename = lib_with_abs_filename[0:36]

                lib_4 = '__' + lib_with_abs_filename + '_' * (38 - len(lib_with_abs_filename))
                new_names[lib_4] = addr

                lib_with_used_filename = lib_filename.used + ':' + lib
                lib_with_used_filename = lib_with_used_filename[0:36]

                lib_4 = '__' + lib_with_used_filename + '_' * (38 - len(lib_with_used_filename))
                new_names[lib_4] = addr

                s = sha3.keccak_256()
                s.update(lib_with_abs_filename.encode('utf-8'))
                lib_5 = "__$" + s.hexdigest()[:34] + "$__"
                new_names[lib_5] = addr

                s = sha3.keccak_256()
                s.update(lib_with_used_filename.encode('utf-8'))
                lib_5 = "__$" + s.hexdigest()[:34] + "$__"
                new_names[lib_5] = addr

        return new_names

    def _library_name_lookup(self, lib_name, original_contract):
        """
        Convert a library name to the contract
        The library can be:
        - the original contract name
        - __X__ following Solidity 0.4 format
        - __$..$__ following Solidity 0.5 format
        :param lib_name:
        :return: contract name (None if not found)
        """

        for name in self.contracts_names:
            if name == lib_name:
                return name

            # Some platform use only the contract name
            # Some use fimename:contract_name
            name_with_absolute_filename = self.contracts_filenames[name].absolute + ':' + name
            name_with_absolute_filename = name_with_absolute_filename[0:36]

            name_with_used_filename = self.contracts_filenames[name].used + ':' + name
            name_with_used_filename = name_with_used_filename[0:36]

            # Solidity 0.4
            if '__' + name + '_' * (38-len(name)) == lib_name:
                return name

            # Solidity 0.4 with filename
            if '__' + name_with_absolute_filename+ '_' * (38-len(name_with_absolute_filename)) == lib_name:
                return name

            # Solidity 0.4 with filename
            if '__' + name_with_used_filename+ '_' * (38-len(name_with_used_filename)) == lib_name:
                return name


            # Solidity 0.5
            s = sha3.keccak_256()
            s.update(name.encode('utf-8'))
            v5_name = "__$" + s.hexdigest()[:34] + "$__"

            if  v5_name == lib_name:
                return name

            # Solidity 0.5 with filename
            s = sha3.keccak_256()
            s.update(name_with_absolute_filename .encode('utf-8'))
            v5_name = "__$" + s.hexdigest()[:34] + "$__"

            if  v5_name == lib_name:
                return name

            s = sha3.keccak_256()
            s.update(name_with_used_filename.encode('utf-8'))
            v5_name = "__$" + s.hexdigest()[:34] + "$__"

            if v5_name == lib_name:
                return name

        # handle specific case of colission for Solidity <0.4
        # We can only detect that the second contract is meant to be the library
        # if there is only two contracts in the codebase
        if len(self._contracts_name) == 2:
            return next((c for c in self._contracts_name if c != original_contract), None)

        return None

    def libraries_names(self, name):
        """
        Return the name of the libraries used by the contract
        :param name: contract
        :return: list of libraries name
        """

        if name not in self._libraries:
            init = re.findall(r'__.{36}__', self.bytecode_init(name))
            runtime = re.findall(r'__.{36}__', self.bytecode_runtime(name))
            self._libraries[name] = [self._library_name_lookup(x, name) for x in set(init+runtime)]
        return self._libraries[name]


    def _update_bytecode_with_libraries(self, bytecode, libraries):
        if libraries:
            libraries = self._convert_libraries_names(libraries)
            for library_found in re.findall(r'__.{36}__', bytecode):
                if library_found in libraries:
                    bytecode = re.sub(
                        re.escape(library_found),
                        '{:040x}'.format(libraries[library_found]),
                        bytecode
                    )
        return bytecode

    # endregion
    ###################################################################################
    ###################################################################################
    # region Hashes
    ###################################################################################
    ###################################################################################

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

    # endregion
    ###################################################################################
    ###################################################################################
    # region Import
    ###################################################################################
    ###################################################################################

    @staticmethod
    def import_archive_compilations(compiled_archive):
        # If the argument is a string, it is likely a filepath, load the archive.
        if isinstance(compiled_archive, str):
            with open(compiled_archive, encoding='utf8') as f:
                compiled_archive = json.load(f)

        # Verify the compiled archive is of the correct form
        if not isinstance(compiled_archive, dict) or 'compilations' not in compiled_archive:
            raise ValueError("Cannot import compiled archive, invalid format.")

        return [CryticCompile((compiled_archive, i)) for i in range(0, len(compiled_archive['compilations']))]

    def _import_archive_compilation(self, compiled_archive, compilation_index):
        compilation = compiled_archive['compilations'][compilation_index]
        self._asts = compilation['asts']
        self._compiler_version = CompilerVersion(compiler=compilation['compiler']['compiler'],
                                                 version=compilation['compiler']['version'],
                                                 optimized=compilation['compiler']['optimized'])
        for contract_name, contract in compilation['contracts'].items():
            self._contracts_name.add(contract_name)
            filename = Filename(absolute=contract['filenames']['absolute'],
                                relative=contract['filenames']['used'],
                                short=contract['filenames']['short'],
                                used=contract['filenames']['relative'])
            self._contracts_filenames[contract_name] = filename

            self._abis[contract_name] = contract['abi']
            self._init_bytecodes[contract_name] = contract['bin']
            self._runtime_bytecodes[contract_name] = contract['bin-runtime']
            self._srcmaps[contract_name] = contract['srcmap'].split(';')
            self._srcmaps_runtime[contract_name] = contract['srcmap-runtime'].split(';')

            archive.set_dependency_status(filename.absolute, contract['is_dependency'])

        # Set all our filenames
        self._filenames = set(self._contracts_filenames.values())

        self._working_dir = compilation['working_dir']
        self._type = compilation['type']
        self._platform = archive

    # endregion

    ###################################################################################
    ###################################################################################
    # region Export
    ###################################################################################
    ###################################################################################

    @staticmethod
    def export_all(compilations, **kwargs):
        # Obtain arguments
        export_format = kwargs.get('export_format', None)

        # Define our return values
        results = {
            'compilations': []
        }

        # Determine if we are exporting a singular archive, or exporting each individually.
        if export_format == 'archive':
            # Create our source file dictionary
            results['source_files'] = {}

            # If we are to export source..
            for compilation in compilations:
                compilation_data = compilation.export(export_format='crytic-compile')
                results['compilations'].append(compilation_data)

                # Next set all source content
                for filename_absolute, source_content in compilation.src_content.items():
                    results['source_files'][filename_absolute] = source_content

            # If we have an export directory specified, we output the JSON to a file.
            export_dir = kwargs.get('export_dir', None)
            if export_dir:
                if not os.path.exists(export_dir):
                    os.makedirs(export_dir)
                path = os.path.join(export_dir, "contracts.ccarchive")
                with open(path, 'w', encoding='utf8') as f:
                    json.dump(results, f)

        else:
            # We are not exporting an archive, each compilation can be exported itself.
            for compilation in compilations:
                compilation_data = compilation.export(**kwargs)
                results['compilations'].append(compilation_data)

        return results

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
        if export_format is None or export_format == "crytic-compile":
            return self._export_standard(**kwargs)
        elif export_format == "solc":
            return solc.export(self, **kwargs)
        elif export_format == "truffle":
            return truffle.export(self, **kwargs)
        else:
            raise Exception('Export format unknown')

    def _export_standard(self, **kwargs):
        # Obtain objects to represent each contract
        contracts = dict()
        for contract_name in self.contracts_names:
            filename = self.filename_of_contract(contract_name)
            contracts[contract_name] = {
                'abi': self.abi(contract_name),
                'bin': self.bytecode_init(contract_name),
                'bin-runtime': self.bytecode_runtime(contract_name),
                'srcmap': ";".join(self.srcmap_init(contract_name)),
                'srcmap-runtime': ";".join(self.srcmap_runtime(contract_name)),
                'filenames': {
                    'absolute': filename.absolute,
                    'used': filename.used,
                    'short': filename.short,
                    'relative': filename.used
                },
                'is_dependency': self._platform.is_dependency(filename.absolute)
            }

        # Create our root object to contain the contracts and other information.
        output = {
            'asts': self._asts,
            'contracts': contracts,
            'compiler': {
                'compiler': self._compiler_version.compiler,
                'version': self._compiler_version.version,
                'optimized': self._compiler_version.optimized,
            },
            'working_dir': str(self._working_dir),
            'type': int(self._type)
        }

        # If we have an export directory specified, we output the JSON to a file.
        export_dir = kwargs.get('export_dir', None)
        if export_dir:
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            path = os.path.join(export_dir, "contracts.json")
            with open(path, 'w', encoding='utf8') as f:
                json.dump(output, f)

        return output

    # endregion
    ###################################################################################
    ###################################################################################
    # region Compile
    ###################################################################################
    ###################################################################################

    @staticmethod
    def compile_all(target, **kwargs):
        """
        Given a direct or glob pattern target, compiles all underlying sources and returns
        all the relevant instances of CryticCompile.
        :param target: A string representing a file/directory path or glob pattern denoting where compilation should
        occur.
        :param kwargs: The remainder of the arguments passed through to all compilation steps.
        :return: Returns a list of CryticCompile instances for all compilations which occurred.
        """
        # Attempt to perform glob expansion of target/filename
        globbed_targets = glob.glob(target, recursive=True)

        # Check if the target refers to a valid target already.
        # If it does not, we assume it's a glob pattern.
        compilations = []
        if os.path.isfile(target) or is_supported(target):
            if is_archive(target):
                compilations += CryticCompile.import_archive_compilations(target)
            else:
                compilations.append(CryticCompile(target, **kwargs))
        elif os.path.isdir(target) or len(globbed_targets) > 0:
            # We create a new glob to find solidity files at this path (in case this is a directory)
            filenames = glob.glob(os.path.join(target, "*.sol"))
            if not filenames:
                filenames = globbed_targets

            # We compile each file and add it to our compilations.
            for filename in filenames:
                compilations.append(CryticCompile(filename, **kwargs))
        else:
            raise ValueError(f"Unresolved target: {str(target)}")

        return compilations

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
                self._platform = truffle
            elif compile_force_framework == 'embark':
                self._platform = embark
            elif compile_force_framework == 'dapp':
                self._platform = dapp
            elif compile_force_framework == 'etherlime':
                self._platform = etherlime
            elif compile_force_framework == 'etherscan':
                self._platform = etherscan
        else:
            # truffle directory
            if not truffle_ignore and truffle.is_truffle(target):
                self._platform = truffle
            # embark directory
            elif not embark_ignore and embark.is_embark(target):
                self._platform = embark
            # dap directory
            elif not dapp_ignore and dapp.is_dapp(target):
                self._platform = dapp
            #etherlime directory
            elif not etherlime_ignore and etherlime.is_etherlime(target):
                self._platform = etherlime
            elif not etherscan_ignore and etherscan.is_etherscan(target):
                self._platform = etherscan
            # .json or .sol provided
            else:
                self._platform = solc

        self._platform.compile(self, target, **kwargs)
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


    # endregion
    ###################################################################################
    ###################################################################################
    # region Metadata
    ###################################################################################
    ###################################################################################

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


    # endregion
    ###################################################################################
    ###################################################################################