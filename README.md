# Crytic-compile
[![Build Status](https://img.shields.io/github/workflow/status/crytic/crytic-compile/CI/master)](https://github.com/crytic/crytic-compile/actions?query=workflow%3ACI)
[![Slack Status](https://empireslacking.herokuapp.com/badge.svg)](https://empireslacking.herokuapp.com)
[![PyPI version](https://badge.fury.io/py/crytic-compile.svg)](https://badge.fury.io/py/crytic-compile)

Library to help smart contract compilation. It includes support for:
- Direct solc compilation
- [Truffle](https://truffleframework.com/)
- [Embark](https://embark.status.im/)
- [Dapp](https://dapp.tools/dapp/)
- [Etherlime](https://github.com/LimeChain/etherlime)
- [Etherscan](https://etherscan.io/)
- [Brownie](https://github.com/iamdefinitelyahuman/brownie)
- [Waffle](https://github.com/EthWorks/Waffle)

See the [Configuration](https://github.com/crytic/crytic-compile/wiki/Configuration) documentation for advanced usages.

The plugin is used in Crytic tools, including:
- [Slither](https://github.com/crytic/slither)
- [Echidna](https://github.com/crytic/echidna)
- [Manticore](https://github.com/trailofbits/manticore/)
- [evm-cfg-builder](https://github.com/crytic/evm_cfg_builder)


## Installation

```
pip3 install crytic-compile
```

## Usage

### Standalone
```bash
$ crytic-compile .
```

Crytic-compile will generate `crytic-export/contracts.json` containing the AST/ABI and bytecodes of the contracts.

Run `crytic-compile --help` for more options.

### As a library

See the [library documentation](https://github.com/crytic/crytic-compile/wiki/Library-Documentation).
