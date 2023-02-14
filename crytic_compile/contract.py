"""
Module handling the source unit
"""
import re
from typing import Dict, List, Optional, Union, Tuple, Set, TYPE_CHECKING
import cbor2

from Crypto.Hash import keccak

from crytic_compile.utils.natspec import Natspec
if TYPE_CHECKING:
    from crytic_compile.source_unit import SourceUnit
from crytic_compile.utils.naming import combine_filename_name

# pylint: disable=too-many-instance-attributes,too-many-public-methods
class Contract:
    """The Contract class represents a single compiled contract within a source unit
    
    Attributes
    ----------
    source_unit: SourceUnit
        A pointer to the associated SourceUnit
    contract_name: str
        The contract's name
    abi: Dict
        The application binary interface (ABI) of the contract
    init_bytecode: str
        The initialization bytecode for the contract
    runtime_bytecode: str
        The runtime bytecode of the contract
    srcmap_init: str
        The initialization source mapping of the contract
    srcmap_runtime: str
        The runtime source mapping of the contract
    natspec: Natspec
        The NatSpec for the contract
    function_hashes: Dict
        The contract's function signatures and their associated hashes
    events: Dict
        The contract's event signatures and their associated hashes
    placeholder_set: Set[str]
        The set of library placeholders identified in the contract
    """

    def __init__(self, source_unit: "SourceUnit", contract_name: str, abi: Dict, init_bytecode: str, runtime_bytecode: str, srcmap_init: str, srcmap_runtime: str, natspec: Natspec):
        """Initialize the Contract class"""
        
        self._source_unit: SourceUnit = source_unit
        self._contract_name: str = contract_name
        self._abi: Dict = abi
        self._init_bytecode: str = init_bytecode
        self._runtime_bytecode: str = runtime_bytecode
        self._srcmap_init: str = srcmap_init
        self._srcmap_runtime: str = srcmap_runtime
        self._natspec: Natspec = natspec
        self._function_hashes: Dict = self._compute_function_hashes()
        self._events: Dict = self._compute_topics_events()
        self._placeholder_set: Set[str] = self._compute_placeholder_set()
        # TODO: Maybe introduce metadata in a future PR

    # region Getters
    ###################################################################################
    ###################################################################################

    @property
    def source_unit(self) -> SourceUnit:
        """Return the SourceUnit associated with this Contract object

        Returns:
            SourceUnit: Pointer to the associated SourceUnit
        """
        return self._source_unit

    @property
    def contract_name(self) -> str:
        """Return the name of the contract

        Returns:
            str: Contract name
        """
        return self._contract_name

    @property
    def abi(self) -> Dict:
        """Return the ABI of the contract

        Returns:
            Dict: ABI
        """
        return self._abi
  
    @property
    def init_bytecode(self) -> SourceUnit:
        """Return the init bytecode of the contract

        Returns:
            str: Init bytecode
        """
        return self._init_bytecode
  
    @property
    def runtime_bytecode(self) -> SourceUnit:
        """Return the runtime bytecode of the contract

        Returns:
            str: Runtime bytecode
        """
        return self._runtime_bytecode

    @property
    def srcmap_init(self) -> str:
        """Return the init source mapping of the contract

        Returns:
            str: The initialization source mapping
        """
        return self._srcmap_init
    
    @property
    def srcmap_runtime(self) -> str:
        """Return the runtime source mapping of the contract

        Returns:
            str: The runtime source mapping
        """
        return self._srcmap_runtime

    @property
    def natspec(self) -> Natspec:
        """Returns the Natspec associated with the contract

        Returns:
            Natspec: Natspec of contract
        """
        return self._natspec

    @property
    def function_hashes(self) -> Dict[str, int]:
        """Return a mapping of function signatures to keccak hashes within a contract

        Returns:
            Dict[str, int]: Mapping of function signature to keccak hash
        """
        return self._function_hashes

    @property
    def events(self) -> Dict[str, Tuple[int, List[bool]]]:
        """Return a mapping of event signatures to keccak hashes within the contract

        Returns:
            Dict[str, Tuple[int, List[bool]]]: Mapping of event signature to keccak hash in addition to which input parameters are indexed
        """
        return self._events

    @property
    def placeholder_set(self) -> Set(str):
        """Returns any library placeholders found in the contract

        Returns:
            Set(str): Set of library placeholders
        """
        return self._placeholder_set


    # endregion
    ###################################################################################
    ###################################################################################

    # region Internal functions
    ###################################################################################
    ###################################################################################
    
    def _compute_placeholder_set(self) -> Set[str]:
        """Returns all library placeholders within the init bytecode of the contract.

        If there are different placeholders within the runtime bytecode of a contract, which is true for a compilation platform like Brownie,
        then this function will not find those placeholders.

        Returns:
            Set[str]: This is the list of placeholders identified in the init bytecode of the contract
        """
        
        # Use regex to find __PLACEHOLDER__ strings
        init = re.findall(r"__(\$[0-9a-zA-Z]*\$|\w*)__", self.init_bytecode)
        return set(init)

    def _compute_function_hashes(self) -> Dict[str, int]:
        """Compute the function hashes

        Returns:
            Dict[str, int]: Returns a dictionary mapping the function signature to the keccak hash as a 256-bit integer
        """

        function_hashes: Dict[str, int] = {}
        
        # Iterate through each key in the ABI
        for function in self._abi:
            function_type = function.get("type", "N/A")
            # If the object describes a function
            if function_type == "function":
                # Grab the name
                try:
                    function_name = function["name"]
                except KeyError:
                    raise KeyError
                
                # Create a comma-delimited string containing all the input arguments
                try:
                    function_args = ",".join([input["type"] for input in function["inputs"]])
                except KeyError:
                    raise KeyError
                
                # Format and hash the function signature
                sig = f"{function_name}({function_args})"
                sha3_result = keccak.new(digest_bits=256)
                sha3_result.update(sig.encode("utf-8"))
                
                # Update mapping
                function_hashes[sig] = int("0x" + sha3_result.hexdigest()[:8], 16)

        return function_hashes

    def _compute_topics_events(self) -> Dict[str, Tuple[int, List[bool]]]:
        """Computes each event's signature, keccak hash, and which parameters are indexed

        Returns:
            Dict[str, Tuple[int, List[bool]]]: Returns a mapping from event signature to a tuple where the integer is the 256-bit keccak
            hash and the list tells you which parameters are indexed
        """
        events: Dict[str, Tuple[int, List[bool]]] = {}
        
        # Iterate through each key in the ABI
        for event in self._abi:
            event_type = event.get("type", "N/A")
            # If the object describes an event
            if event_type == "event":
                # Grab the name
                try:
                    event_name = event["name"]
                except KeyError:
                    raise KeyError
                
                # Create a comma-delimited string containing all the input arguments
                try:
                    event_args = ",".join([input["type"] for input in event["inputs"]])
                except KeyError:
                    raise KeyError
                
                # Figure out which input arguments are indexed
                indexed = [input.get("indexed", False) for input in event["inputs"]]
                
                # Format and hash the event signature
                sig = f"{event_name}({event_args})"
                sha3_result = keccak.new(digest_bits=256)
                sha3_result.update(sig.encode("utf-8"))
                
                # Update mapping
                events[sig] = (int("0x" + sha3_result.hexdigest()[:8], 16), indexed)

        return events
    
    # endregion
    ###################################################################################
    ###################################################################################
    
    # region Metadata
    ###################################################################################
    ###################################################################################

    # TODO: Metadata parsing is broken. Needs to be fixed in a separate PR
    def metadata_of(self, name: str) -> Dict[str, Union[str, bool]]:
        return None

    def remove_metadata(self) -> None:
        return None

    # endregion
    ###################################################################################
    ###################################################################################