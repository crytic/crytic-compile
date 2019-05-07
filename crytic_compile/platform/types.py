from enum import Enum

class Type(Enum):
    SOLC = 1
    TRUFFLE = 2
    EMBARK = 3
    DAPP = 4
    ETHERLIME = 5
    ETHERSCAN = 6

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
        raise ValueError
