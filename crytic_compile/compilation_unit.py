import uuid
from typing import List
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, Set, Optional

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.contract import Contract
from crytic_compile.utils.naming import Filename

# Cycle dependency
if TYPE_CHECKING:
    from crytic_compile import CryticCompile
    from crytic_compile.source_unit import SourceUnit

# pylint: disable=too-many-instance-attributes
class CompilationUnit:
    """The CompilationUnit class represents a "call" to the compiler. 
    
    Attributes
    ----------
    crytic_compile: CryticCompile
        A pointer to the associated CryticCompile object
    source_units: Dict[Filename, SourceUnit]
        The mapping of a Filename object to the associated SourceUnit
    compiler_version: CompilerVersion
        A pointer to the CompilerVersion object
    unique_id: str
        The unique identifier provided to this CompilationUnit
    """
    
    def __init__(self, crytic_compile: "CryticCompile", unique_id: str):
        """Initialize the CompilationUnit object"""
        
        self._crytic_compile: "CryticCompile" = crytic_compile
        self.source_units: Dict[Filename, SourceUnit] = {}
        # TODO: Fix compiler_version public / private capabilities
        self.compiler_version: CompilerVersion = CompilerVersion(
            compiler="N/A", version="N/A", optimized=False
        )
        # Libraries used by the contract
        # contract_name -> (library, pattern)
        self._libraries: Dict[str, List[Tuple[str, str]]] = {}
 
        if unique_id == ".":
            unique_id = str(uuid.uuid4())
        self._unique_id = unique_id

        # TODO: Make the addition of a `CompilationUnit` happen in each `compile()` function instead of `__init__`
        crytic_compile.compilation_units[unique_id] = self  # type: ignore

    # region Getters
    ###################################################################################
    ###################################################################################
    
    @property
    def crytic_compile(self) -> "CryticCompile":
        """Return the CryticCompile object associated with this CompilationUnit

        Returns:
            CryticCompile: Pointer to the CryticCompile object
        """
        return self._crytic_compile
    
    @property
    def unique_id(self) -> str:
        """Return the compilation unit ID

        Returns:
            str: Compilation unit unique ID
        """
        return self._unique_id

    @property
    def asts(self) -> Dict[str, Dict]:
        """
        Return all the asts from the compilation unit

        Returns:
            Dict[str, Dict]: absolute path -> ast
        """
        return {
            source_unit.filename.absolute: source_unit.ast
            for source_unit in self.source_units.values()
        }
    
    # endregion
    ###################################################################################
    ###################################################################################
    
    # region Filenames
    ###################################################################################
    ###################################################################################

    @property
    def filenames(self) -> Set[Filename]:
        """Return the filenames used by the compilation unit

        Returns:
            Set[Filename]: Filenames used by the compilation units
        """
        return set(self.source_units.keys())

    def filename_to_contracts(self) -> Dict[Filename, List[ContractUnit]]:
        """Return a dict mapping the filename to a list of contract declared

        Returns:
            Dict[Filename, List[str]]: Filename -> List[contract_name]
        """
        filename_to_contracts: Dict[Filename, List[ContractUnit]] = {}
        for filename, source_unit in self.source_units.items():
            filename_to_contracts[filename] = source_unit.contracts.values()
        
        return filename_to_contracts

    def filename_lookup(self, filename: str) -> Filename:
        """Return a crytic_compile.naming.Filename from a any filename

        Args:
            filename (str): filename (used/absolute/relative)

        Raises:
            ValueError: If the filename is not in the project

        Returns:
            Filename: Associated Filename object
        """
        # pylint: disable=import-outside-toplevel
        from crytic_compile.platform.truffle import Truffle

        if isinstance(self.crytic_compile.platform, Truffle) and filename.startswith("project:/"):
            filename = filename[len("project:/") :]

        if self._filenames_lookup is None:
            self._filenames_lookup = {}
            for file in self._filenames:
                self._filenames_lookup[file.absolute] = file
                self._filenames_lookup[file.relative] = file
                self._filenames_lookup[file.used] = file
        if filename not in self._filenames_lookup:
            raise ValueError(
                f"{filename} does not exist in {[f.absolute for f in self._filenames_lookup.values()]}"
            )
        return self._filenames_lookup[filename]

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
            Dict[str, List[Tuple[str, str]]]:  (contract_name -> [(library, placeholder))])
        """
        return self._libraries
    
    def _library_placeholders_legacy(self, library_name: str, filename: Filename) -> Optional[Dict[str, str]]:
        """Return a list of all possible placeholders for a given library name for Solidity version 0.4.x and below. There are a total of three possibilities:
        library name, absolute path of the library, or the path used during compilation.

        Args:
            library_name (str): The name of the library
            filename (Filename): A Filename object that holds the absolute / used filepaths for the given library

        Returns:
            Optional[Dict[str, str]]: Returns a dictionary of all possible placeholders. Returns an empty dictionary if library_name is empty or None
        """

        
        # Guard clause
        if library_name == "" or library_name is None:
            return None
        
        # Get absolute and used source paths
        absolute_srcpath = filename.absolute + ":" + library_name
        used_srcpath = filename.used + ":" + library_name
        if len(absolute_srcpath) > 36:
            absolute_srcpath = absolute_srcpath[:36]
        if len(used_srcpath) > 36:
            used_srcpath = used_srcpath[:36]
        
        retVal = {}
        # The basic placeholder is __LibraryName____
        retVal["basicPlaceholder"] = "__" + library_name + "_" * (38 - len(library_name))

        # The absolute srcpath placeholder is __absolutePath:LibraryName__
        retVal["absoluteSrcPathPlaceholder"] = (
            "__"
            + absolute_srcpath
            + "_" * (38 - len(absolute_srcpath))
        )

        # The used srcpath placeholder is __usedPath:LibraryName__
        retVal["usedSrcPathPlaceholder"] = (
            "__" + used_srcpath + "_" * (38 - len(used_srcpath))
        )
        
        return retVal

    def _library_placeholders_latest(self, library_name: str, filename: Filename) -> Optional[Dict[str, str]]:
        """Return a list of all possible placeholders for a given library name for Solidity version 0.5.x and above. There are a total of three possibilities:
        keccak hash of the library name, keccak hash of the absolute path of the library, or the keccak hash of the path used during compilation.

        Args:
            library_name (str): The name of the library
            filename (Filename): A Filename object that holds the absolute / used filepaths for the given library

        Returns:
            Dict[str, str]: Returns a dictionary of all possible placeholders. Returns None if library_name is empty or None
        """
        
        # Guard clause
        if library_name == "" or library_name is None:
            return None
        
        # Get absolute and used source paths
        absolute_srcpath = filename.absolute + ":" + library_name
        used_srcpath = filename.used + ":" + library_name
        
        retVal = {}
        # The basic placeholder is __keccak256(LibraryName)__
        sha3_result = keccak.new(digest_bits=256)
        sha3_result.update(library_name.encode("utf-8"))
        retVal["basicPlaceholder"] = "__$" + sha3_result.hexdigest()[:34] + "$__"

        # The absolute srcpath placeholder is __keccak256(absolutePath:LibraryName)__
        sha3_result = keccak.new(digest_bits=256)
        sha3_result.update(absolute_srcpath.encode("utf-8"))
        retVal["absoluteSrcPathPlaceholder"] = "__$" + sha3_result.hexdigest()[:34] + "$__"

        # The used srcpath placeholder is __keccak256(usedPath:LibraryName)__
        sha3_result = keccak.new(digest_bits=256)
        sha3_result.update(used_srcpath.encode("utf-8"))
        retVal["usedSrcPathPlaceholder"] = "__$" + sha3_result.hexdigest()[:34] + "$__"

        return retVal
    
    def _library_placeholder_lookup(
        self, placeholder: str, original_contract: str
    ) -> Optional[str]:
        """Identify the library that is associated with a given placeholder

        Args:
            placeholder (str): placeholder
            original_contract (str): original contract name where the placeholder was derived from

        Returns:
            Optional[str]: library name associated with a given placeholder
        """

        compiler_version = self.compilation_unit.compiler_version

        # Guard clause to ignore library lookups when the compiler is not `solc` or if semantic version is not set
        if compiler_version.compiler != "solc" or compiler_version.compiler_version is None:
            return None
        
        for filename, contract_names in self.compilation_unit.filename_to_contracts().items():
            for contract_name in contract_names:
                # Call `latest` if solidity version is 0.5.x and above or `legacy` if version is 0.4.x and below
                # `placeholders` is the list of possible placeholders associated with a given contract_name
                if compiler_version.version.major == 0 and compiler_version.version.minor > 4:
                    placeholders = self._library_placeholders_latest(contract_name, filename)
                elif compiler_version.version.major == 0 and compiler_version.version.minor <= 4:
                    placeholders = self._library_placeholders_legacy(contract_name, filename)
                else:
                    placeholders = None
                
                if placeholders and placeholder in placeholders.values():
                    return contract_name
        
        # Handle edge case for Solidity version < 0.4 as a last-ditch effort
        if compiler_version.version.major == 0 and compiler_version.version.minor < 4:
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

    def libraries_names_and_placeholders(self, contract_name: str) -> List[Tuple[str, str]]:
        """Return the library names and their associated placeholders in a given contract. Also sets self._libraries for the given contract_name

        Args:
            name (str): contract name

        Returns:
            List[Tuple[str, str]]: (library_name, pattern)
        """
        if contract_name in self._libraries:
            return self._libraries[contract_name]
            
        init = re.findall(r"__.{36}__", self._init_bytecodes[contract_name])
        runtime = re.findall(r"__.{36}__", self._runtime_bytecodes(contract_name))
        for placeholder in set(init + runtime):
            library_name = self._library_placeholder_lookup(placeholder, contract_name)
            if library_name:
                self._libraries[contract_name].append((library_name, placeholder))
        return self._libraries[contract_name]

    # endregion
    ###################################################################################
    ###################################################################################

