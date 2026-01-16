# crytic-compile

Compilation abstraction layer for smart contracts. Provides a unified interface to compile Solidity/Vyper projects across multiple build systems (solc, Foundry, Hardhat, Truffle, etc.) and fetch verified contracts from on-chain sources (Etherscan, Sourcify).

Used by Slither, Echidna, Manticore, and other Trail of Bits tools.

## Architecture

```
crytic_compile/
├── crytic_compile.py      # Main CryticCompile class, compile_all()
├── compilation_unit.py    # CompilationUnit - one compiler invocation
├── source_unit.py         # SourceUnit - one source file's compiled data
├── compiler/              # CompilerVersion metadata
├── platform/              # Platform implementations
│   ├── abstract_platform.py   # AbstractPlatform base class
│   ├── types.py               # Type enum (platform priority)
│   ├── solc.py                # Direct solc compilation
│   ├── foundry.py             # Foundry/Forge
│   ├── hardhat.py             # Hardhat (v2 and v3)
│   ├── truffle.py             # Truffle
│   ├── etherscan.py           # Etherscan API
│   ├── sourcify.py            # Sourcify API
│   └── ...                    # Other platforms
├── utils/
│   ├── naming.py          # Filename dataclass (path normalization)
│   ├── natspec.py         # NatSpec comment handling
│   └── zip.py             # Archive import/export
└── cryticparser/          # CLI argument parsing
```

## Development

| tool    | purpose          |
|---------|------------------|
| `uv`    | deps & venv      |
| `ruff`  | lint & format    |
| `ty`    | type check       |
| `pytest`| tests            |

```bash
# Setup (using uv)
uv sync --extra dev

# Linting & formatting
uv run ruff check crytic_compile/
uv run ruff format --check .
uv run ty check crytic_compile/

# Auto-fix
uv run ruff check --fix crytic_compile/
uv run ruff format .

# Tests
uv run pytest --cov=crytic_compile tests/

# Or use pip if preferred
pip install -e ".[dev]"
ruff check crytic_compile/
ty check crytic_compile/
pytest tests/
```

### Navigating the codebase

```bash
# Find platform implementations
ast-grep --pattern 'class $NAME(AbstractPlatform): $$$' --lang py crytic_compile/platform

# Find where platforms are detected
rg "is_supported" crytic_compile/platform

# Find compilation flow
ast-grep --pattern 'def compile($$$): $$$' --lang py crytic_compile

# Trace data structures
rg "class CompilationUnit" crytic_compile
rg "class SourceUnit" crytic_compile
```

## Code Standards

### Philosophy
- **No speculative features** - Don't add "might be useful" functionality
- **Minimal dependencies** - Only pycryptodome, cbor2, solc-select
- **Platform abstraction** - All frameworks produce identical `CompilationUnit` output
- **Path normalization** - Use `Filename` dataclass, not raw strings

### Code quality
- **Type hints required** - Parameters, returns, class variables, lists, sets. Dictionaries when possible.
- **Google-style docstrings** - For non-obvious operations
- **Comments** - No commented-out code. Code should be self-documenting.
- **Errors** - Raise `InvalidCompilation` for compilation failures with clear messages.

### Hard limits
1. 100-char line length
2. No relative (`..`) imports
3. Type hints on function signatures (enforced by ty)

### Linting

Uses ruff for linting/formatting and ty for type checking:

```bash
ruff check crytic_compile/           # Lint
ruff format --check .                # Check formatting
ty check crytic_compile/             # Type check
```

Config in `pyproject.toml`:
- ruff: E, F, W, I, UP rules (ignores E501 line length)
- ty: Python 3.10 target

## Working on Code

### Git conventions
- Work from `master` branch (main development trunk)
- One logical change per PR
- Minimize formatting changes in unrelated code
- Large changes should be split into smaller PRs

### Adding a new platform

1. Add type to `platform/types.py`:
   ```python
   class Type(IntEnum):
       MY_PLATFORM = 14  # Next available

       def priority(self) -> int:
           if self == Type.MY_PLATFORM:
               return 250  # Lower = higher priority
   ```

2. Create `platform/myplatform.py`:
   ```python
   class MyPlatform(AbstractPlatform):
       NAME = "MyPlatform"
       PROJECT_URL = "https://..."
       TYPE = Type.MY_PLATFORM

       @staticmethod
       def is_supported(target: str, **kwargs: str) -> bool:
           """Detect via marker file"""
           return os.path.isfile(os.path.join(target, "myconfig.toml"))

       def compile(self, crytic_compile: "CryticCompile", **kwargs: str) -> None:
           """Run build and populate compilation units"""
           ...

       def clean(self, **kwargs: str) -> None:
           ...

       def is_dependency(self, path: str) -> bool:
           return "node_modules" in Path(path).parts

       def _guessed_tests(self) -> list[str]:
           return ["myplatform test"]
   ```

3. Import in `platform/all_platforms.py` and add to `__all__`

## Testing

Tests live in `/tests/`. Run specific framework tests via CI scripts in `/scripts/ci_*.sh`.

```bash
pytest tests/test_library_linking.py -v   # Specific test
pytest -k metadata                        # Pattern match
```

## crytic-compile Internals

### Data model

```
CryticCompile
 └── compilation_units: dict[str, CompilationUnit]
      └── source_units: dict[Filename, SourceUnit]
           ├── abis: dict[str, dict]           # Contract ABIs
           ├── bytecodes_init: dict[str, str]  # Creation bytecode
           ├── bytecodes_runtime: dict[str, str]
           ├── srcmaps_init: dict[str, list[str]]
           ├── srcmaps_runtime: dict[str, list[str]]
           ├── ast: dict                        # Compiler AST
           └── natspec: dict[str, Natspec]
```

### Key classes

- **CryticCompile** (`crytic_compile.py`) - Entry point. Detects platform, orchestrates compilation.
- **CompilationUnit** (`compilation_unit.py`) - One compiler invocation. Multiple possible per project (e.g., different solc versions).
- **SourceUnit** (`source_unit.py`) - Compiled data for one file. Access bytecodes, ABIs, source maps.
- **Filename** (`utils/naming.py`) - Path normalization. Use instead of raw strings.

### Platform detection flow

1. `--compile-force-framework` flag checked first
2. Platforms sorted by priority (Foundry 100 > Hardhat 200 > Truffle 300 > others 1000)
3. Each platform's `is_supported(target)` called in order
4. First match wins, or fallback to Solc

### Common patterns

**Iterate all contracts:**
```python
cc = CryticCompile(target)
for compilation_unit in cc.compilation_units.values():
    for source_unit in compilation_unit.source_units.values():
        for contract_name in source_unit.contracts_names:
            abi = source_unit.abis[contract_name]
            bytecode = source_unit.bytecode_runtime(contract_name)
```

**Get bytecode with libraries linked:**
```python
libraries = {"SafeMath": "0xdeadbeef..."}
bytecode = source_unit.bytecode_runtime(contract_name, libraries)
```

**Access source mappings:**
```python
srcmap = source_unit.srcmaps_runtime[contract_name]  # list[str]
# Each entry: "start:length:file_index:jump_type"
```

### Export formats

- **standard** - crytic-compile JSON format
- **solc** - solc JSON output format
- **truffle** - Truffle artifact format

```python
cc.export(export_format="standard", export_dir="crytic-export")
```

### Platform config extraction

Platforms can provide `config()` to extract settings (for Slither to use raw solc):
```python
config = Foundry.config(working_dir)
# Returns: PlatformConfig(solc_version, optimizer, remappings, ...)
```

## Notes

**Python version**: 3.10+ (3.12.0 excluded due to Windows bug)

**Build system**: hatchling (pyproject.toml)

**Dependencies**: Minimal - pycryptodome (keccak), cbor2 (metadata), solc-select (compiler management)

**Lockfile**: `uv.lock` for reproducible builds

---

> Don't push until asked.
