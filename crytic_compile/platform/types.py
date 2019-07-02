from enum import IntEnum


class Type(IntEnum):
    SOLC = 1
    TRUFFLE = 2
    EMBARK = 3
    DAPP = 4
    ETHERLIME = 5
    ETHERSCAN = 6
    STANDARD = 7
    ARCHIVE = 8
    VYPER = 9

    def __str__(self):
        if self == Type.SOLC:
            return 'solc'
        if self == Type.TRUFFLE:
            return 'Truffle'
        if self == Type.EMBARK:
            return 'Embark'
        if self == Type.DAPP:
            return 'Dapp'
        if self == Type.ETHERLIME:
            return 'Etherlime'
        if self == Type.ETHERSCAN:
            return 'Etherscan'
        if self == Type.STANDARD:
            return 'Standard'
        if self == Type.ARCHIVE:
            return 'Archive'
        if self == Type.VYPER:
            return 'Archive'
        raise ValueError
