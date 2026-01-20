"""
Module containing all the platforms
"""

# Re-exports for dynamic platform discovery - DO NOT REMOVE
# crytic_compile.py uses dir(all_platforms) to find these classes
__all__ = [
    "Archive",
    "Brownie",
    "Buidler",
    "Dapp",
    "Embark",
    "Etherlime",
    "Etherscan",
    "Foundry",
    "Hardhat",
    "Solc",
    "SolcStandardJson",
    "Sourcify",
    "Standard",
    "Truffle",
    "VyperStandardJson",
    "Waffle",
]

from .archive import Archive
from .brownie import Brownie
from .buidler import Buidler
from .dapp import Dapp
from .embark import Embark
from .etherlime import Etherlime
from .etherscan import Etherscan
from .foundry import Foundry
from .hardhat import Hardhat
from .solc import Solc
from .solc_standard_json import SolcStandardJson
from .sourcify import Sourcify
from .standard import Standard
from .truffle import Truffle
from .vyper import VyperStandardJson
from .waffle import Waffle
