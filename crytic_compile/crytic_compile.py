import copy
import os
import json
import glob
import logging
import re
import subprocess
import sha3
from pathlib import Path

from .platform import solc, truffle, embark, dapp, etherlime, etherscan, archive, standard, vyper
from .utils.zip import load_from_zip

logger = logging.getLogger("CryticCompile")
logging.basicConfig()


def is_supported(target):
    supported = [solc.is_solc,
                 truffle.is_truffle,
                 embark.is_embark,
                 dapp.is_dapp,
                 etherlime.is_etherlime,
                 etherscan.is_etherscan,
                 standard.is_standard,
                 archive.is_archive,
                 vyper.is_vyper]
    return any(f(target) for f in supported) or target.endswith('.zip')

PLATFORMS = {'solc': solc,
             'truffle': truffle,
             'embark': embark,
             'dapp': dapp,
             'etherlime': etherlime,
             'etherscan': etherscan,
             'archive': archive,
             'standard': standard,
             'vyper': vyper}

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
        if target.endswith('.zip'):
            compilations = load_from_zip(target)
        else:
            compilations.append(CryticCompile(target, **kwargs))
    elif os.path.isdir(target) or len(globbed_targets) > 0:
        # We create a new glob to find solidity files at this path (in case this is a directory)
        filenames = glob.glob(os.path.join(target, "*.sol"))
        if not filenames:
            filenames = glob.glob(os.path.join(target, "*.vy"))
            if not filenames:
                filenames = globbed_targets

        # We compile each file and add it to our compilations.
        for filename in filenames:
            compilations.append(CryticCompile(filename, **kwargs))
    else:
        raise ValueError(f"Unresolved target: {str(target)}")

    return compilations


class CryticCompile:

    def __init__(self, target, **kwargs):
        '''
            Args:
                target (str)
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
        # dependencies is needed for platform conversion
        self._dependencies = set()

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

        self._target = target

        self._working_dir = Path.cwd()

        # If its a exported archive, we use compilation index 0.
        if isinstance(target, dict):
            target = (target, 0)

        self._compile(target, **kwargs)

    @property
    def target(self):
        return self._target

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
        return filename in self._dependencies or self._platform.is_dependency(filename)

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

    def src_content_for_file(self, filename_absolute):
        return self.src_content.get(filename_absolute, None)

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
        :return: (contract name, pattern) (None if not found)
        """

        for name in self.contracts_names:
            if name == lib_name:
                return (name, name)

            # Some platform use only the contract name
            # Some use fimename:contract_name
            name_with_absolute_filename = self.contracts_filenames[name].absolute + ':' + name
            name_with_absolute_filename = name_with_absolute_filename[0:36]

            name_with_used_filename = self.contracts_filenames[name].used + ':' + name
            name_with_used_filename = name_with_used_filename[0:36]

            # Solidity 0.4
            solidity_0_4 = '__' + name + '_' * (38-len(name))
            if solidity_0_4 == lib_name:
                return (name, solidity_0_4)

            # Solidity 0.4 with filename
            solidity_0_4_filename = '__' + name_with_absolute_filename+ '_' * (38-len(name_with_absolute_filename))
            if solidity_0_4_filename == lib_name:
                return (name, solidity_0_4_filename)

            # Solidity 0.4 with filename
            solidity_0_4_filename = '__' + name_with_used_filename + '_' * (38 - len(name_with_used_filename))
            if solidity_0_4_filename == lib_name:
                return (name, solidity_0_4_filename)


            # Solidity 0.5
            s = sha3.keccak_256()
            s.update(name.encode('utf-8'))
            v5_name = "__$" + s.hexdigest()[:34] + "$__"

            if v5_name == lib_name:
                return (name, v5_name)

            # Solidity 0.5 with filename
            s = sha3.keccak_256()
            s.update(name_with_absolute_filename .encode('utf-8'))
            v5_name = "__$" + s.hexdigest()[:34] + "$__"

            if v5_name == lib_name:
                return (name, v5_name)

            s = sha3.keccak_256()
            s.update(name_with_used_filename.encode('utf-8'))
            v5_name = "__$" + s.hexdigest()[:34] + "$__"

            if v5_name == lib_name:
                return (name, v5_name)

        # handle specific case of collision for Solidity <0.4
        # We can only detect that the second contract is meant to be the library
        # if there is only two contracts in the codebase
        if len(self._contracts_name) == 2:
            return next(((c, '__' + c + '_' * (38-len(c))) for c in self._contracts_name if c != original_contract),
                        None)

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
        return [name for (name, pattern) in self._libraries[name]]

    def libraries_names_and_patterns(self, name):
        """
        Return the name of the libraries used by the contract
        :param name: contract
        :return: list of (libraries name, pattern)
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

    # endregion

    ###################################################################################
    ###################################################################################
    # region Export
    ###################################################################################
    ###################################################################################

    def export(self, **kwargs):
        """
            Export to json.
            The json format can be crytic-compile, solc or truffle.
            solc format is --combined-json bin-runtime,bin,srcmap,srcmap-runtime,abi,ast,compact-format
            Keyword Args:
                export_format (str): export format (default None). Accepted: None, 'solc', 'truffle',
                'crytic-compile', 'standard'
                export_dir (str): export dir (default crytic-export)
        """
        export_format = kwargs.get('export_format', None)
        if export_format is None or export_format in ["crytic-compile", "standard"]:
            return standard.export(self, **kwargs)
        elif export_format == "solc":
            return solc.export(self, **kwargs)
        elif export_format == "truffle":
            return truffle.export(self, **kwargs)
        elif export_format == "archive":
            return archive.export(self, **kwargs)
        else:
            raise Exception('Export format unknown')



    # endregion
    ###################################################################################
    ###################################################################################
    # region Compile
    ###################################################################################
    ###################################################################################

    def _compile(self, target, **kwargs):

        truffle_ignore = kwargs.get('truffle_ignore', False)
        embark_ignore = kwargs.get('embark_ignore', False)
        dapp_ignore = kwargs.get('dapp_ignore', False)
        etherlime_ignore = kwargs.get('etherlime_ignore', False)
        etherscan_ignore = kwargs.get('etherscan_ignore', False)
        standard_ignore = kwargs.get('standard_ignore', False)
        archive_ignore = kwargs.get('standard_ignore', False)
        vyper_ignore = kwargs.get('vyper_ignore', False)

        custom_build = kwargs.get('compile_custom_build', None)

        if custom_build:
            truffle_ignore = True
            embark_ignore = True
            dapp_ignore = True
            etherlime_ignore = True
            etherscan_ignore = True
            standard_ignore = True
            archive_ignore = True
            vyper_ignore = True

            self._run_custom_build(custom_build)

        compile_force_framework = kwargs.get('compile_force_framework', None)
        if compile_force_framework and compile_force_framework in PLATFORMS:
            self._platform = PLATFORMS[compile_force_framework]
        else:
            if not truffle_ignore and truffle.is_truffle(target):
                self._platform = truffle
            elif not embark_ignore and embark.is_embark(target):
                self._platform = embark
            elif not dapp_ignore and dapp.is_dapp(target):
                self._platform = dapp
            elif not etherlime_ignore and etherlime.is_etherlime(target):
                self._platform = etherlime
            elif not etherscan_ignore and etherscan.is_etherscan(target):
                self._platform = etherscan
            elif not standard_ignore and standard.is_standard(target):
                self._platform = standard
            elif not archive_ignore and archive.is_archive(target):
                self._platform = archive
            elif not vyper_ignore and vyper.is_vyper(target):
                self._platform = vyper
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