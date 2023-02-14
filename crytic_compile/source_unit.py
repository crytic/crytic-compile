"""
Module handling the source unit
"""
import re
from typing import Dict, List, Optional, Union, Tuple, Set, TYPE_CHECKING
import cbor2

from Crypto.Hash import keccak

from crytic_compile.utils.naming import Filename
from crytic_compile.utils.natspec import Natspec

if TYPE_CHECKING:
    from crytic_compile.compilation_unit import CompilationUnit
    from crytic_compile.contract import Contract


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class SourceUnit:
    """The SourceUnit class represents a set of contracts within a single file
    
    Attributes
    ----------
    compilation_unit: CompilationUnit
        A pointer to the associated CompilationUnit
    filename: Filename
        The Filename object associated with this SourceUnit
    ast: Dict
        The abstract syntax tree (AST) of the SourceUnit
    contracts: Dict[str, Contract]
        The mapping of contract name to the Contract
    """

    def __init__(self, compilation_unit: "CompilationUnit", filename: Filename, ast: Dict):
        """Initialize the SourceUnit class"""
        
        self._compilation_unit: "CompilationUnit" = compilation_unit
        self._filename: Filename = filename
        self._ast: Dict = ast
        self.contracts: Dict[str, Contract] = {}

    # region Getters
    ###################################################################################
    ###################################################################################
    
    @property
    def compilation_unit(self) -> CompilationUnit:
        """Return the CompilationUnit associated with this SourceUnit

        Returns:
            CompilationUnit: Pointer to the associated CompilationUnit
        """
        return self._compilation_unit

    @property
    def filename(self) -> Filename:
        """Return the Filename associated with this SourceUnit

        Returns:
            Filename: Filename object
        """
        return self._filename
    
    @property
    def ast(self) -> Dict:
        """Return the AST associated with this SourceUnit

        Returns:
            Dict: AST
        """
        return self._ast
    
    # endregion
    ###################################################################################
    ###################################################################################
