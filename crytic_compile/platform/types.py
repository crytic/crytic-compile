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

    STANDARD = 100
    ARCHIVE = 101

    def __str__(self):
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
        raise ValueError
