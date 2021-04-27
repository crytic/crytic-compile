import re
import uuid
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, Union

import sha3

from crytic_compile.utils.naming import Filename
from crytic_compile.utils.natspec import Natspec
from crytic_compile.compiler.compiler import CompilerVersion

# Cycle dependency
if TYPE_CHECKING:
    from crytic_compile import CryticCompile

# pylint: disable=too-many-instance-attributes,too-many-public-methods
class CompilationUnit:
    def __init__(self, crytic_compile: "CryticCompile", unique_id: str):
        # ASTS are indexed by absolute path
        self._asts: Dict = {}

        # ABI, bytecode and srcmap are indexed by contract_name
        self._abis: Dict = {}
        self._runtime_bytecodes: Dict = {}
        self._init_bytecodes: Dict = {}
        self._hashes: Dict = {}
        self._events: Dict = {}
        self._srcmaps: Dict[str, List[str]] = {}
        self._srcmaps_runtime: Dict[str, List[str]] = {}

        # set containing all the contract names
        self._contracts_name: Set[str] = set()
        # set containing all the contract name without the libraries
        self._contracts_name_without_libraries: Optional[Set[str]] = None

        # mapping from contract name to filename (naming.Filename)
        self._contracts_filenames: Dict[str, Filename] = {}

        # Libraries used by the contract
        # contract_name -> (library, pattern)
        self._libraries: Dict[str, List[Tuple[str, str]]] = {}

        # Natspec
        self._natspec: Dict[str, Natspec] = {}

        # compiler.compiler
        self._compiler_version: CompilerVersion = CompilerVersion(
            compiler="N/A", version="N/A", optimized=False
        )

        self._crytic_compile: "CryticCompile" = crytic_compile

        if unique_id == ".":
            unique_id = uuid.uuid4()

        crytic_compile.compilation_units[unique_id] = self

        self._unique_id = unique_id

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def crytic_compile(self) -> "CryticCompile":
        return self._crytic_compile

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
        if used_filename in self._crytic_compile.filenames:
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
    # region Events
    ###################################################################################
    ###################################################################################

    def events_topics(self, name: str) -> Dict[str, Tuple[int, List[bool]]]:
        """
        Return the topics of the contract'sevents
        :param name: contract
        :return: A dictionary {event signature -> topic hash, [is_indexed for each parameter]}
        """
        if not name in self._events:
            self._compute_topics_events(name)
        return self._events[name]

    def _compute_topics_events(self, name: str):
        self._events[name] = {}
        for sig in self.abi(name):
            if "type" in sig:
                if sig["type"] == "event":
                    sig_name = sig["name"]
                    arguments = ",".join([x["type"] for x in sig["inputs"]])
                    indexes = [x.get("indexed", False) for x in sig["inputs"]]
                    sig = f"{sig_name}({arguments})"
                    sha3_result = sha3.keccak_256()
                    sha3_result.update(sig.encode("utf-8"))

                    self._events[name][sig] = (int("0x" + sha3_result.hexdigest()[:8], 16), indexes)

    # endregion
    ###################################################################################
    ###################################################################################
    # region Metadata
    ###################################################################################
    ###################################################################################

    def remove_metadata(self):
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
    # region Compiler information
    ###################################################################################
    ###################################################################################

    @property
    def compiler_version(self) -> "CompilerVersion":
        """
        Return the compiler used as a namedtuple(compiler, version)

        :return:
        """
        return self._compiler_version

    @compiler_version.setter
    def compiler_version(self, compiler):
        self._compiler_version = compiler
