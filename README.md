# Crytic-compile
[![Build Status](https://travis-ci.com/crytic/crytic-compile.svg?branch=master)](https://travis-ci.com/crytic/crytic-compile)
[![Slack Status](https://empireslacking.herokuapp.com/badge.svg)](https://empireslacking.herokuapp.com)


[WORK IN PROGRESS]

Library to help smart contract compilation. It includes support for:
- Direct solc compilation
- [Truffle](https://truffleframework.com/)
- [Embark](https://embark.status.im/)

The plugin is used in Crytic tools, including:
- [Slither](https://github.com/crytic/slither)
- [evm-cfg-builder](https://github.com/crytic/evm_cfg_builder)

## Installation

```
pip install crytic-compile
```

## Usage

### Standalone
```bash
$ crytic-compile .
```

Crytic-compile will generate `crytic-export/contracts.json` containing the AST/ABI and bytecodes of the contracts.
The file structure is:
```json
{
    "asts": [],
    "contracts": [
        "/path:contract_name":
        {
            "abi": [],
            "bin": ..,
            "bin-runtime": ..
        }
}
```

Run `crytic-compile --help` for more options.

### As a library

See the library documentation (TODO).
