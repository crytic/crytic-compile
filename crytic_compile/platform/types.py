"""
Handle the platform type
"""

from enum import IntEnum


class Type(IntEnum):
    """
    Represent the different platform
    """

    NOT_IMPLEMENTED = 0
    SOLC = 1
    TRUFFLE = 2
    EMBARK = 3
    DAPP = 4
    ETHERLIME = 5
    ETHERSCAN = 6
    VYPER = 7
    WAFFLE = 8
    BROWNIE = 9
    SOLC_STANDARD_JSON = 10
    BUILDER = 11
    HARDHAT = 11

    STANDARD = 100
    ARCHIVE = 101

    def __str__(self) -> str:  # pylint: disable=too-many-branches
        """Return a string representation

        Raises:
            ValueError: If the type is missing in __str__ (it should not happen)

        Returns:
            str: string representation
        """
        if self == Type.SOLC:
            return "solc"
        if self == Type.SOLC_STANDARD_JSON:
            return "solc_standard_json"
        if self == Type.TRUFFLE:
            return "Truffle"
        if self == Type.EMBARK:
            return "Embark"
        if self == Type.DAPP:
            return "Dapp"
        if self == Type.ETHERLIME:
            return "Etherlime"
        if self == Type.ETHERSCAN:
            return "Etherscan"
        if self == Type.STANDARD:
            return "Standard"
        if self == Type.ARCHIVE:
            return "Archive"
        if self == Type.VYPER:
            return "Archive"
        if self == Type.WAFFLE:
            return "Waffle"
        if self == Type.BUILDER:
            return "Builder"
        if self == Type.BROWNIE:
            return "Browner"
        raise ValueError
