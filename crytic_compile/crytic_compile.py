"""
CryticCompile main module. Handle the compilation.
"""
import inspect
import os
import json
import glob
import logging
import re
import subprocess
from typing import Dict, List, Union, Set, Tuple, Optional, Type, TYPE_CHECKING
from pathlib import Path
import sha3

from .platform import solc_standard_json, all_platforms
from .platform.abstract_platform import AbstractPlatform
from .platform.all_export import PLATFORMS_EXPORT
from .platform.solc import Solc
from .platform.standard import export_to_standard
from .utils.naming import Filename
from .utils.natspec import Natspec
from .utils.zip import load_from_zip
from .utils.npm import get_package_name

# Cycle dependency
if TYPE_CHECKING:
    from .compiler.compiler import CompilerVersion

LOGGER = logging.getLogger("CryticCompile")
logging.basicConfig()


def get_platforms() -> List[Type[AbstractPlatform]]:
    """
    Return the available platforms classes

    :return:
    """
    platforms = [getattr(all_platforms, name) for name in dir(all_platforms)]
    platforms = [d for d in platforms if inspect.isclass(d) and issubclass(d, AbstractPlatform)]
    return sorted(platforms, key=lambda platform: platform.TYPE)


def is_supported(target: str) -> bool:
    """
    Check if the target is supported

    :param target:
    :return:
    """
    platforms = get_platforms()
    return any(platform.is_supported(target) for platform in platforms) or target.endswith(".zip")


class CryticCompile:
    """
    Main class.
    """

    def __init__(self, target: Union[str, AbstractPlatform], **kwargs: str):
        """
            Args:
                target (str|SolcStandardJson)
            Keyword Args:
                See https://github.com/crytic/crytic-compile/wiki/Configuration
        """
        # ASTS are indexed by absolute path
        self._asts: Dict = {}

        # ABI, bytecode and srcmap are indexed by contract_name
        self._abis: Dict = {}
        self._runtime_bytecodes: Dict = {}
        self._init_bytecodes: Dict = {}
        self._hashes: Dict = {}
        self._srcmaps: Dict[str, List[str]] = {}
        self._srcmaps_runtime: Dict[str, List[str]] = {}
        self._src_content: Dict = {}
        # dependencies is needed for platform conversion
        self._dependencies: Set = set()

        # set containing all the contract names
        self._contracts_name: Set[str] = set()
        # set containing all the contract name without the libraries
        self._contracts_name_without_libraries: Optional[Set[str]] = None

        # set containing all the filenames
        self._filenames: Set[Filename] = set()
        # mapping from contract name to filename (naming.Filename)
        self._contracts_filenames: Dict[str, Filename] = {}

        # Libraries used by the contract
        # contract_name -> (library, pattern)
        self._libraries: Dict[str, List[Tuple[str, str]]] = {}

        self._bytecode_only = False

        # Natspec
        self._natspec: Dict[str, Natspec] = {}

        # compiler.compiler
        self._compiler_version: Optional["CompilerVersion"] = None

        self._working_dir = Path.cwd()

        if isinstance(target, str):
            platform = self._init_platform(target, **kwargs)
        else:
            platform = target

        self._package = get_package_name(platform.target)

        self._platform: AbstractPlatform = platform

        # If its a exported archive, we use compilation index 0.
        # if isinstance(target, dict):
        #    target = (target, 0)

        self._compile(**kwargs)

    @property
    def target(self) -> str:
        """
        Return the target (project)

        :return:
        """
        return self._platform.target

    ###################################################################################
    ###################################################################################
    # region Natspec
    ###################################################################################
    ###################################################################################

    @property
    def natspec(self):
        """
        Return the natspec of the contractse

        :return: Dict[str, Natspec]
        """
        return self._natspec

    ###################################################################################
    ###################################################################################
    # region Filenames
    ###################################################################################
    ###################################################################################

    @property
    def filenames(self) -> Set[Filename]:
        """
        :return: set(naming.Filename)
        """
        return self._filenames

    @filenames.setter
    def filenames(self, all_filenames: Set[Filename]):
        self._filenames = all_filenames

    @property
    def contracts_filenames(self) -> Dict[str, Filename]:
        """
        Return a dict contract_name -> Filename namedtuple (absolute, used)

        :return: dict(name -> utils.namings.Filename)
        """
        return self._contracts_filenames

    @property
    def contracts_absolute_filenames(self) -> Dict[str, str]:
        """
        Return a dict (contract_name -> absolute filename)

        :return:
        """
        return {k: f.absolute for (k, f) in self._contracts_filenames.items()}

    def filename_of_contract(self, name: str) -> Filename:
        """
        :return: utils.namings.Filename
         """
        return self._contracts_filenames[name]

    def absolute_filename_of_contract(self, name: str) -> str:
        """
        :return: Absolute filename
         """
        return self._contracts_filenames[name].absolute

    def used_filename_of_contract(self, name: str) -> str:
        """
        :return: Used filename
         """
        return self._contracts_filenames[name].used

    def find_absolute_filename_from_used_filename(self, used_filename: str) -> str:
        """
        Return the absolute filename based on the used one

        :param used_filename:
        :return: absolute filename
        """
        # Note: we could memoize this function if the third party end up using it heavily
        # If used_filename is already an absolute pathn no need to lookup
        if used_filename in self._filenames:
            return used_filename
        d_file = {f.used: f.absolute for _, f in self._contracts_filenames.items()}
        if used_filename not in d_file:
            raise ValueError("f{filename} does not exist in {d}")
        return d_file[used_filename]

    def relative_filename_from_absolute_filename(self, absolute_filename: str) -> str:
        """
        Return the relative file based on the absolute name

        :param absolute_filename:
        :return:
        """
        d_file = {f.absolute: f.relative for _, f in self._contracts_filenames.items()}
        if absolute_filename not in d_file:
            raise ValueError("f{absolute_filename} does not exist in {d}")
        return d_file[absolute_filename]

    def filename_lookup(self, filename: str) -> Filename:
        """
        Return a crytic_compile.naming.Filename from a any filename form (used/absolute/relative)

        :param filename: str
        :return: crytic_compile.naming.Filename
        """
        d_file = {}
        for file in self._filenames:
            d_file[file.absolute] = file
            d_file[file.relative] = file
            d_file[file.used] = file
        if filename not in d_file:
            raise ValueError(f"{filename} does not exist in {d_file}")
        return d_file[filename]

    @property
    def dependencies(self) -> Set[str]:
        """
        Return the dependencies files

        :return:
        """
        return self._dependencies

    def is_dependency(self, filename: str) -> bool:
        """
        Check if the filename is a dependency

        :param filename:
        :return:
        """
        return filename in self._dependencies or self.platform.is_dependency(filename)

    @property
    def package(self) -> Optional[str]:
        """
        Return the package name

        :return:
        """
        return self._package

    @property
    def working_dir(self) -> Path:
        """
        Return the working dir

        :return:
        """
        return self._working_dir

    @working_dir.setter
    def working_dir(self, path: Path):
        self._working_dir = path

    # endregion
    ###################################################################################
    ###################################################################################
    # region Contract Names
    ###################################################################################
    ###################################################################################

    @property
    def contracts_names(self) -> Set[str]:
        """
        Return the contracts names

        :return:
        """
        return self._contracts_name

    @contracts_names.setter
    def contracts_names(self, names: Set[str]):
        """
        Return the contracts names

        :return:
        """
        self._contracts_name = names

    @property
    def contracts_names_without_libraries(self) -> Set[str]:
        """
        Return the contracts names (without the librairies)

        :return:
        """
        if self._contracts_name_without_libraries is None:
            libraries: List[str] = []
            for contract_name in self._contracts_name:
                libraries += self.libraries_names(contract_name)
            self._contracts_name_without_libraries = {
                l for l in self._contracts_name if l not in set(libraries)
            }
        return self._contracts_name_without_libraries

    # endregion
    ###################################################################################
    ###################################################################################
    # region ABI
    ###################################################################################
    ###################################################################################

    @property
    def abis(self) -> Dict:
        """
        Return the ABIs

        :return:
        """
        return self._abis

    def abi(self, name: str) -> Dict:
        """
        Get the ABI from a contract

        :param name:
        :return:
        """
        return self._abis.get(name, None)

    # endregion
    ###################################################################################
    ###################################################################################
    # region AST
    ###################################################################################
    ###################################################################################

    @property
    def asts(self) -> Dict:
        """
        Return the ASTs

        :return: dict (absolute filename -> AST)
        """
        return self._asts

    @asts.setter
    def asts(self, value: Dict):
        self._asts = value

    def ast(self, path: str) -> Union[Dict, None]:
        """
        Return of the file

        :param path:
        :return:
        """
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
    def bytecodes_runtime(self) -> Dict[str, str]:
        """
        Return the runtime bytecodes

        :return:
        """
        return self._runtime_bytecodes

    @bytecodes_runtime.setter
    def bytecodes_runtime(self, bytecodes: Dict[str, str]):
        """
        Return the init bytecodes

        :return:
        """
        self._runtime_bytecodes = bytecodes

    @property
    def bytecodes_init(self) -> Dict[str, str]:
        """
        Return the init bytecodes

        :return:
        """
        return self._init_bytecodes

    @bytecodes_init.setter
    def bytecodes_init(self, bytecodes: Dict[str, str]):
        """
        Return the init bytecodes

        :return:
        """
        self._init_bytecodes = bytecodes

    def bytecode_runtime(self, name: str, libraries: Union[None, Dict[str, str]] = None) -> str:
        """
        Return the runtime bytecode of the contract. If library is provided, patch the bytecode

        :param name:
        :param libraries:
        :return:
        """
        runtime = self._runtime_bytecodes.get(name, None)
        return self._update_bytecode_with_libraries(runtime, libraries)

    def bytecode_init(self, name: str, libraries: Union[None, Dict[str, str]] = None) -> str:
        """
        Return the init bytecode of the contract. If library is provided, patch the bytecode

        :param name:
        :param libraries:
        :return:
        """
        init = self._init_bytecodes.get(name, None)
        return self._update_bytecode_with_libraries(init, libraries)

    # endregion
    ###################################################################################
    ###################################################################################
    # region Source mapping
    ###################################################################################
    ###################################################################################

    @property
    def srcmaps_init(self) -> Dict[str, List[str]]:
        """
        Return the init srcmap

        :return:
        """
        return self._srcmaps

    @property
    def srcmaps_runtime(self) -> Dict[str, List[str]]:
        """
        Return the runtime srcmap

        :return:
        """
        return self._srcmaps_runtime

    def srcmap_init(self, name: str) -> List[str]:
        """
        Return the init srcmap

        :param name:
        :return:
        """
        return self._srcmaps.get(name, [])

    def srcmap_runtime(self, name: str) -> List[str]:
        """
        Return the runtime srcmap

        :param name:
        :return:
        """
        return self._srcmaps_runtime.get(name, [])

    @property
    def src_content(self) -> Dict[str, str]:
        """
        Return the source content, filename -> source_code

        :return:
        """
        # If we have no source code loaded yet, load it for every contract.
        if not self._src_content:
            for name in self.contracts_names:
                filename = self.filename_of_contract(name)
                if filename.absolute not in self._src_content and os.path.isfile(filename.absolute):
                    with open(filename.absolute, encoding="utf8", newline="") as source_file:
                        self._src_content[filename.absolute] = source_file.read()
        return self._src_content

    @src_content.setter
    def src_content(self, src):
        """
        Set the src_content

        :param src:
        :return:
        """
        self._src_content = src

    def src_content_for_file(self, filename_absolute: str) -> Union[str, None]:
        """
        Get the source code of the file

        :param filename_absolute:
        :return:
        """
        return self.src_content.get(filename_absolute, None)

    # endregion
    ###################################################################################
    ###################################################################################
    # region Type
    ###################################################################################
    ###################################################################################

    @property
    def type(self) -> int:
        """
        Return the type of the platform used

        :return:
        """
        # Type should have been set by now
        assert self._platform.TYPE
        return self._platform.TYPE

    @property
    def platform(self) -> AbstractPlatform:
        """
        Return the platform module

        :return:
        """
        assert self._platform
        return self._platform

    # endregion
    ###################################################################################
    ###################################################################################
    # region Compiler information
    ###################################################################################
    ###################################################################################

    @property
    def compiler_version(self) -> Union[None, "CompilerVersion"]:
        """
        Return the compiler used as a namedtuple(compiler, version)

        :return:
        """
        return self._compiler_version

    @compiler_version.setter
    def compiler_version(self, compiler):
        self._compiler_version = compiler

    @property
    def bytecode_only(self) -> bool:
        """
        Return true if only the bytecode was retrieved

        :return:
        """
        return self._bytecode_only

    @bytecode_only.setter
    def bytecode_only(self, bytecode):
        self._bytecode_only = bytecode

    # endregion
    ###################################################################################
    ###################################################################################
    # region Libraries
    ###################################################################################
    ###################################################################################

    @property
    def libraries(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        Return the libraries used (contract_name -> [(library, pattern))])

        :return:
        """
        return self._libraries

    def _convert_libraries_names(self, libraries: Dict[str, str]) -> Dict[str, str]:
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

            lib_4 = "__" + lib + "_" * (38 - len(lib))

            sha3_result = sha3.keccak_256()
            sha3_result.update(lib.encode("utf-8"))
            lib_5 = "__$" + sha3_result.hexdigest()[:34] + "$__"

            new_names[lib] = addr
            new_names[lib_4] = addr
            new_names[lib_5] = addr

            if lib in self.contracts_names:
                lib_filename = self.contracts_filenames[lib]

                lib_with_abs_filename = lib_filename.absolute + ":" + lib
                lib_with_abs_filename = lib_with_abs_filename[0:36]

                lib_4 = "__" + lib_with_abs_filename + "_" * (38 - len(lib_with_abs_filename))
                new_names[lib_4] = addr

                lib_with_used_filename = lib_filename.used + ":" + lib
                lib_with_used_filename = lib_with_used_filename[0:36]

                lib_4 = "__" + lib_with_used_filename + "_" * (38 - len(lib_with_used_filename))
                new_names[lib_4] = addr

                sha3_result = sha3.keccak_256()
                sha3_result.update(lib_with_abs_filename.encode("utf-8"))
                lib_5 = "__$" + sha3_result.hexdigest()[:34] + "$__"
                new_names[lib_5] = addr

                sha3_result = sha3.keccak_256()
                sha3_result.update(lib_with_used_filename.encode("utf-8"))
                lib_5 = "__$" + sha3_result.hexdigest()[:34] + "$__"
                new_names[lib_5] = addr

        return new_names

    def _library_name_lookup(
        self, lib_name: str, original_contract: str
    ) -> Optional[Tuple[str, str]]:
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
                return name, name

            # Some platform use only the contract name
            # Some use fimename:contract_name
            name_with_absolute_filename = self.contracts_filenames[name].absolute + ":" + name
            name_with_absolute_filename = name_with_absolute_filename[0:36]

            name_with_used_filename = self.contracts_filenames[name].used + ":" + name
            name_with_used_filename = name_with_used_filename[0:36]

            # Solidity 0.4
            solidity_0_4 = "__" + name + "_" * (38 - len(name))
            if solidity_0_4 == lib_name:
                return name, solidity_0_4

            # Solidity 0.4 with filename
            solidity_0_4_filename = (
                "__" + name_with_absolute_filename + "_" * (38 - len(name_with_absolute_filename))
            )
            if solidity_0_4_filename == lib_name:
                return name, solidity_0_4_filename

            # Solidity 0.4 with filename
            solidity_0_4_filename = (
                "__" + name_with_used_filename + "_" * (38 - len(name_with_used_filename))
            )
            if solidity_0_4_filename == lib_name:
                return name, solidity_0_4_filename

            # Solidity 0.5
            sha3_result = sha3.keccak_256()
            sha3_result.update(name.encode("utf-8"))
            v5_name = "__$" + sha3_result.hexdigest()[:34] + "$__"

            if v5_name == lib_name:
                return name, v5_name

            # Solidity 0.5 with filename
            sha3_result = sha3.keccak_256()
            sha3_result.update(name_with_absolute_filename.encode("utf-8"))
            v5_name = "__$" + sha3_result.hexdigest()[:34] + "$__"

            if v5_name == lib_name:
                return name, v5_name

            sha3_result = sha3.keccak_256()
            sha3_result.update(name_with_used_filename.encode("utf-8"))
            v5_name = "__$" + sha3_result.hexdigest()[:34] + "$__"

            if v5_name == lib_name:
                return name, v5_name

        # handle specific case of collision for Solidity <0.4
        # We can only detect that the second contract is meant to be the library
        # if there is only two contracts in the codebase
        if len(self._contracts_name) == 2:
            return next(
                (
                    (c, "__" + c + "_" * (38 - len(c)))
                    for c in self._contracts_name
                    if c != original_contract
                ),
                None,
            )

        return None

    def libraries_names(self, name: str) -> List[str]:
        """
        Return the name of the libraries used by the contract

        :param name: contract
        :return: list of libraries name
        """

        if name not in self._libraries:
            init = re.findall(r"__.{36}__", self.bytecode_init(name))
            runtime = re.findall(r"__.{36}__", self.bytecode_runtime(name))
            libraires = [self._library_name_lookup(x, name) for x in set(init + runtime)]
            self._libraries[name] = [lib for lib in libraires if lib]
        return [name for (name, pattern) in self._libraries[name]]

    def libraries_names_and_patterns(self, name):
        """
        Return the name of the libraries used by the contract

        :param name: contract
        :return: list of (libraries name, pattern)
        """

        if name not in self._libraries:
            init = re.findall(r"__.{36}__", self.bytecode_init(name))
            runtime = re.findall(r"__.{36}__", self.bytecode_runtime(name))
            libraires = [self._library_name_lookup(x, name) for x in set(init + runtime)]
            self._libraries[name] = [lib for lib in libraires if lib]
        return self._libraries[name]

    def _update_bytecode_with_libraries(
        self, bytecode: str, libraries: Union[None, Dict[str, str]]
    ) -> str:
        """
        Patch the bytecode

        :param bytecode:
        :param libraries:
        :return:
        """
        if libraries:
            libraries = self._convert_libraries_names(libraries)
            for library_found in re.findall(r"__.{36}__", bytecode):
                if library_found in libraries:
                    bytecode = re.sub(
                        re.escape(library_found),
                        "{:040x}".format(libraries[library_found]),
                        bytecode,
                    )
        return bytecode

    # endregion
    ###################################################################################
    ###################################################################################
    # region Hashes
    ###################################################################################
    ###################################################################################

    def hashes(self, name: str) -> Dict[str, int]:
        """
        Return the hashes of the functions

        :param name:
        :return:
        """
        if not name in self._hashes:
            self._compute_hashes(name)
        return self._hashes[name]

    def _compute_hashes(self, name: str):
        self._hashes[name] = {}
        for sig in self.abi(name):
            if "type" in sig:
                if sig["type"] == "function":
                    sig_name = sig["name"]
                    arguments = ",".join([x["type"] for x in sig["inputs"]])
                    sig = f"{sig_name}({arguments})"
                    sha3_result = sha3.keccak_256()
                    sha3_result.update(sig.encode("utf-8"))
                    self._hashes[name][sig] = int("0x" + sha3_result.hexdigest()[:8], 16)

    # endregion
    ###################################################################################
    ###################################################################################
    # region Import
    ###################################################################################
    ###################################################################################

    @staticmethod
    def import_archive_compilations(compiled_archive: Union[str, Dict]) -> List["CryticCompile"]:
        """
        Import from an archive. compiled_archive is either a json file or the loaded dictionary
        The dictionary myst contain the "compilations" keyword

        :param compiled_archive:
        :return:
        """
        # If the argument is a string, it is likely a filepath, load the archive.
        if isinstance(compiled_archive, str):
            with open(compiled_archive, encoding="utf8") as file:
                compiled_archive = json.load(file)

        # Verify the compiled archive is of the correct form
        if not isinstance(compiled_archive, dict) or "compilations" not in compiled_archive:
            raise ValueError("Cannot import compiled archive, invalid format.")

        return [CryticCompile(archive) for archive in compiled_archive["compilations"]]

    # endregion

    ###################################################################################
    ###################################################################################
    # region Export
    ###################################################################################
    ###################################################################################

    def export(self, **kwargs: str) -> Optional[str]:
        """
            Export to json. The json format can be crytic-compile, solc or truffle.
        """
        export_format = kwargs.get("export_format", None)
        if export_format is None:
            return export_to_standard(self, **kwargs)
        if export_format not in PLATFORMS_EXPORT:
            raise Exception("Export format unknown")
        return PLATFORMS_EXPORT[export_format](self, **kwargs)

    # endregion
    ###################################################################################
    ###################################################################################
    # region Compile
    ###################################################################################
    ###################################################################################

    def _init_platform(self, target: str, **kwargs: str) -> AbstractPlatform:
        platforms = get_platforms()
        platform = None

        compile_force_framework: Union[str, None] = kwargs.get("compile_force_framework", None)
        if compile_force_framework:
            platform = next(
                (p(target) for p in platforms if p.NAME == compile_force_framework), None
            )

        if not platform:
            platform = next((p(target) for p in platforms if p.is_supported(target)), None)

        if not platform:
            platform = Solc(target)

        return platform

    def _compile(self, **kwargs: str):
        custom_build: Union[None, str] = kwargs.get("compile_custom_build", None)
        if custom_build:
            self._run_custom_build(custom_build)

        else:
            self._platform.compile(self, **kwargs)

        remove_metadata = kwargs.get("compile_remove_metadata", False)
        if remove_metadata:
            self._remove_metadata()

    @staticmethod
    def _run_custom_build(custom_build: str):
        cmd = custom_build.split(" ")

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_bytes, stderr_bytes = process.communicate()
        stdout, stderr = (
            stdout_bytes.decode(),
            stderr_bytes.decode(),
        )  # convert bytestrings to unicode strings

        LOGGER.info(stdout)
        if stderr:
            LOGGER.error("Custom build error: \n%s", stderr)

    # endregion
    ###################################################################################
    ###################################################################################
    # region Metadata
    ###################################################################################
    ###################################################################################

    def _remove_metadata(self):
        """
            Init bytecode contains metadata that needs to be removed
            see
            http://solidity.readthedocs.io/en/v0.4.24/metadata.html#encoding-of-the-metadata-hash-in-the-bytecode
        """
        self._init_bytecodes = {
            key: re.sub(r"a165627a7a72305820.{64}0029", r"", bytecode)
            for (key, bytecode) in self._init_bytecodes.items()
        }

        self._runtime_bytecodes = {
            key: re.sub(r"a165627a7a72305820.{64}0029", r"", bytecode)
            for (key, bytecode) in self._runtime_bytecodes.items()
        }

    # endregion
    ###################################################################################
    ###################################################################################
    # region NPM
    ###################################################################################
    ###################################################################################

    @property
    def package_name(self) -> Optional[str]:
        """
        :return: str or None
        """
        return self._package

    @package_name.setter
    def package_name(self, name: Optional[str]):
        self._package = name


# endregion
###################################################################################
###################################################################################


def compile_all(target: str, **kwargs: str) -> List[CryticCompile]:
    """
    Given a direct or glob pattern target, compiles all underlying sources and returns
    all the relevant instances of CryticCompile.

    :param target: A string representing a file/directory path or glob pattern denoting where compilation shouldoccur.
    :param kwargs: The remainder of the arguments passed through to all compilation steps.
    :return: Returns a list of CryticCompile instances for all compilations which occurred.
    """
    use_solc_standard_json = kwargs.get("solc_standard_json", False)

    # Attempt to perform glob expansion of target/filename
    globbed_targets = glob.glob(target, recursive=True)

    # Check if the target refers to a valid target already.
    # If it does not, we assume it's a glob pattern.
    compilations: List[CryticCompile] = []
    if os.path.isfile(target) or is_supported(target):
        if target.endswith(".zip"):
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

        # Determine if we're using --standard-solc option to
        # aggregate many files into a single compilation.
        if use_solc_standard_json:
            # If we're using standard solc, then we generated our
            # input to create a single compilation with all files
            standard_json = solc_standard_json.SolcStandardJson()
            for filename in filenames:
                standard_json.add_source_file(filename)
            compilations.append(CryticCompile(standard_json, **kwargs))
        else:
            # We compile each file and add it to our compilations.
            for filename in filenames:
                compilations.append(CryticCompile(filename, **kwargs))
    else:
        raise ValueError(f"Unresolved target: {str(target)}")

    return compilations
