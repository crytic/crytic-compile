"""
Module handling the compilation unit
"""
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
    """CompilationUnit class"""

    def __init__(self, crytic_compile: "CryticCompile", unique_id: str):
        """Init the object

        Args:
            crytic_compile (CryticCompile): Associated CryticCompile object
            unique_id (str): Unique ID used to identify the compilation unit
        """
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

        # set containing all the filenames of this compilation unit
        self._filenames: Set[Filename] = set()

        # compiler.compiler
        self._compiler_version: CompilerVersion = CompilerVersion(
            compiler="N/A", version="N/A", optimized=False
        )

        self._crytic_compile: "CryticCompile" = crytic_compile

        if unique_id == ".":
            unique_id = str(uuid.uuid4())

        crytic_compile.compilation_units[unique_id] = self

        self._unique_id = unique_id

    @property
    def unique_id(self) -> str:
        """Return the compilation unit ID

        Returns:
            str: Compilation unit unique ID
        """
        return self._unique_id

    @property
    def crytic_compile(self) -> "CryticCompile":
        """Return the CryticCompile object

        Returns:
            CryticCompile: Associated CryticCompile object
        """
        return self._crytic_compile

    ###################################################################################
    ###################################################################################
    # region Natspec
    ###################################################################################
    ###################################################################################

    @property
    def natspec(self) -> Dict[str, Natspec]:
        """Return the natspec of the contracts

        Returns:
            Dict[str, Natspec]: Contract name -> Natspec
        """
        return self._natspec

    ###################################################################################
    ###################################################################################
    # region Filenames
    ###################################################################################
    ###################################################################################

    @property
    def filenames(self) -> Set[Filename]:
        """Return the filenames used by the compilation units

        Returns:
            Set[Filename]: Filenames used by the compilation units
        """
        return self._filenames

    @filenames.setter
    def filenames(self, all_filenames: Set[Filename]) -> None:
        """Set the filenames

        Args:
            all_filenames (Set[Filename]): new filenames
        """
        self._filenames = all_filenames

    @property
    def contracts_filenames(self) -> Dict[str, Filename]:
        """Return a dict mapping the contract name to their Filename

        Returns:
            Dict[str, Filename]: contract_name -> Filename
        """
        return self._contracts_filenames

    @property
    def contracts_absolute_filenames(self) -> Dict[str, str]:
        """Return a dict mapping the contract name to their absolute filename

        Returns:
            Dict[str, Filename]: contract_name -> absolute filename
        """
        return {k: f.absolute for (k, f) in self._contracts_filenames.items()}

    def filename_of_contract(self, name: str) -> Filename:
        """Return the Filename of a given contract

        Args:
            name (str): Contract name

        Returns:
            Filename: Filename associated with the contract
        """
        return self._contracts_filenames[name]

    def absolute_filename_of_contract(self, name: str) -> str:
        """Return the absolute filename of a given contract

        Args:
            name (str): Contract name

        Returns:
            str: Absolute filename associated with the contract
        """
        return self._contracts_filenames[name].absolute

    def used_filename_of_contract(self, name: str) -> str:
        """Return the used filename of a given contract

        Args:
            name (str): Contract name

        Returns:
            str: Used filename associated with the contract
        """
        return self._contracts_filenames[name].used

    def find_absolute_filename_from_used_filename(self, used_filename: str) -> str:
        """Return the absolute filename based on the used one

        Args:
            used_filename (str): Used filename

        Raises:
            ValueError: If the filename is not found

        Returns:
            str: Absolute filename
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
        """Return the relative file based on the absolute name

        Args:
            absolute_filename (str): Absolute filename

        Raises:
            ValueError: If the filename is not found

        Returns:
            str: Absolute filename
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
        """Return the contracts names

        Returns:
            Set[str]: List of the contracts names
        """
        return self._contracts_name

    @contracts_names.setter
    def contracts_names(self, names: Set[str]) -> None:
        """Set the contract names

        Args:
            names (Set[str]): New contracts names
        """
        self._contracts_name = names

    @property
    def contracts_names_without_libraries(self) -> Set[str]:
        """Return the contracts names without the librairies

        Returns:
            Set[str]: List of contracts
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
        """Return the ABIs

        Returns:
            Dict: ABIs (solc/vyper format) (contract name -> ABI)
        """
        return self._abis

    def abi(self, name: str) -> Dict:
        """Get the ABI from a contract

        Args:
            name (str): Contract name

        Returns:
            Dict: ABI (solc/vyper format)
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
        """Return the ASTs

        Returns:
            Dict: contract name -> AST (solc/vyper format)
        """
        return self._asts

    @asts.setter
    def asts(self, value: Dict) -> None:
        """Set the ASTs

        Args:
            value (Dict): New ASTs
        """
        self._asts = value

    def ast(self, path: str) -> Union[Dict, None]:
        """Return the ast of the file

        Args:
            path (str): path to the file

        Returns:
            Union[Dict, None]: Ast (solc/vyper format)
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
        """Return the runtime bytecodes

        Returns:
            Dict[str, str]: contract => runtime bytecode
        """
        return self._runtime_bytecodes

    @bytecodes_runtime.setter
    def bytecodes_runtime(self, bytecodes: Dict[str, str]) -> None:
        """Set the bytecodes runtime

        Args:
            bytecodes (Dict[str, str]): New bytecodes runtime
        """
        self._runtime_bytecodes = bytecodes

    @property
    def bytecodes_init(self) -> Dict[str, str]:
        """Return the init bytecodes

        Returns:
            Dict[str, str]: contract => init bytecode
        """
        return self._init_bytecodes

    @bytecodes_init.setter
    def bytecodes_init(self, bytecodes: Dict[str, str]) -> None:
        """Set the bytecodes init

        Args:
            bytecodes (Dict[str, str]): New bytecodes init
        """
        self._init_bytecodes = bytecodes

    def bytecode_runtime(self, name: str, libraries: Optional[Dict[str, str]] = None) -> str:
        """Return the runtime bytecode of the contract.
        If library is provided, patch the bytecode

        Args:
            name (str): contract name
            libraries (Optional[Dict[str, str]], optional): lib_name => address. Defaults to None.

        Returns:
            str: runtime bytecode
        """
        runtime = self._runtime_bytecodes.get(name, None)
        return self._update_bytecode_with_libraries(runtime, libraries)

    def bytecode_init(self, name: str, libraries: Optional[Dict[str, str]] = None) -> str:
        """Return the init bytecode of the contract.
        If library is provided, patch the bytecode

        Args:
            name (str): contract name
            libraries (Optional[Dict[str, str]], optional): lib_name => address. Defaults to None.

        Returns:
            str: init bytecode
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
        """Return the srcmaps init

        Returns:
            Dict[str, List[str]]: Srcmaps init (solc/vyper format)
        """
        return self._srcmaps

    @property
    def srcmaps_runtime(self) -> Dict[str, List[str]]:
        """Return the srcmaps runtime

        Returns:
            Dict[str, List[str]]: Srcmaps runtime (solc/vyper format)
        """
        return self._srcmaps_runtime

    def srcmap_init(self, name: str) -> List[str]:
        """Return the srcmap init of a contract

        Args:
            name (str): name of the contract

        Returns:
            List[str]: Srcmap init (solc/vyper format)
        """
        return self._srcmaps.get(name, [])

    def srcmap_runtime(self, name: str) -> List[str]:
        """Return the srcmap runtime of a contract

        Args:
            name (str): name of the contract

        Returns:
            List[str]: Srcmap runtime (solc/vyper format)
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
        """Return the libraries used

        Returns:
            Dict[str, List[Tuple[str, str]]]:  (contract_name -> [(library, pattern))])
        """
        return self._libraries

    def _convert_libraries_names(self, libraries: Dict[str, str]) -> Dict[str, str]:
        """Convert the libraries names
        The name in the argument can be the library name, or filename:library_name
        The returned dict contains all the names possible with the different solc versions

        Args:
            libraries (Dict[str, str]): lib_name => address

        Returns:
            Dict[str, str]: lib_name => address
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
        """Do a lookup on a library name to its name used in contracts
        The library can be:
        - the original contract name
        - __X__ following Solidity 0.4 format
        - __$..$__ following Solidity 0.5 format

        Args:
            lib_name (str): library name
            original_contract (str): original contract name

        Returns:
            Optional[Tuple[str, str]]: contract_name, library_name
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
        """Return the names of the libraries used by the contract

        Args:
            name (str): contract name

        Returns:
            List[str]: libraries used
        """

        if name not in self._libraries:
            init = re.findall(r"__.{36}__", self.bytecode_init(name))
            runtime = re.findall(r"__.{36}__", self.bytecode_runtime(name))
            libraires = [self._library_name_lookup(x, name) for x in set(init + runtime)]
            self._libraries[name] = [lib for lib in libraires if lib]
        return [name for (name, _) in self._libraries[name]]

    def libraries_names_and_patterns(self, name: str) -> List[Tuple[str, str]]:
        """Return the names and the patterns of the libraries used by the contract

        Args:
            name (str): contract name

        Returns:
            List[Tuple[str, str]]: (lib_name, pattern)
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
        """Update the bytecode with the libraries address

        Args:
            bytecode (str): bytecode to patch
            libraries (Union[None, Dict[str, str]]): pattern => address

        Returns:
            str: Patched bytecode
        """
        if libraries:
            libraries = self._convert_libraries_names(libraries)
            for library_found in re.findall(r"__.{36}__", bytecode):
                if library_found in libraries:
                    bytecode = re.sub(
                        re.escape(library_found),
                        "{:040x}".format(int(libraries[library_found])),
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
        """Return the hashes of the functions

        Args:
            name (str): contract name

        Returns:
            Dict[str, int]: (function name => signature)
        """
        if not name in self._hashes:
            self._compute_hashes(name)
        return self._hashes[name]

    def _compute_hashes(self, name: str) -> None:
        """Compute the function hashes

        Args:
            name (str): contract name
        """
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
        """Return the topics of the contract's events

        Args:
            name (str): contract name

        Returns:
            Dict[str, Tuple[int, List[bool]]]: event signature => topic hash, [is_indexed for each parameter]
        """
        if not name in self._events:
            self._compute_topics_events(name)
        return self._events[name]

    def _compute_topics_events(self, name: str) -> None:
        """Compute the topics of the contract's events

        Args:
            name (str): contract name
        """
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

    def remove_metadata(self) -> None:
        """Remove init bytecode
        See
        http://solidity.readthedocs.io/en/v0.4.24/metadata.html#encoding-of-the-metadata-hash-in-the-bytecode

        Note we dont support recent Solidity version, see https://github.com/crytic/crytic-compile/issues/59
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
        """Return the compiler info

        Returns:
            CompilerVersion: compiler info
        """
        return self._compiler_version

    @compiler_version.setter
    def compiler_version(self, compiler: CompilerVersion) -> None:
        """Set the compiler version

        Args:
            compiler (CompilerVersion): New compiler version
        """
        self._compiler_version = compiler
