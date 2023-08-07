"""
Test library linking
"""
import re
from pathlib import Path
import pytest
from crytic_compile.crytic_compile import CryticCompile

TEST_DIR = Path(__file__).resolve().parent

LIBRARY_PLACEHOLDER_REGEX = r"__.{36}__"


def test_library_linking() -> None:
    """Test that the placeholder is not present in the bytecode when the libraries are provided"""
    cc = CryticCompile(
        Path(TEST_DIR / "library_linking.sol").as_posix(),
        compile_libraries="(NeedsLinkingA, 0xdead),(NeedsLinkingB, 0x000000000000000000000000000000000000beef)",
    )
    for compilation_unit in cc.compilation_units.values():
        for source_unit in compilation_unit.source_units.values():
            assert (
                len(re.findall(r"__.{36}__", source_unit.bytecode_init("TestLibraryLinking"))) == 2
            )
            assert (
                len(re.findall(r"__.{36}__", source_unit.bytecode_runtime("TestLibraryLinking")))
                == 2
            )
            libraries = compilation_unit.crytic_compile.libraries
            assert (
                len(
                    re.findall(
                        r"__.{36}__", source_unit.bytecode_init("TestLibraryLinking", libraries)
                    )
                )
                == 0
            )
            assert (
                len(
                    re.findall(
                        r"__.{36}__", source_unit.bytecode_runtime("TestLibraryLinking", libraries)
                    )
                )
                == 0
            )


def test_library_linking_validation() -> None:
    """Test that invalid compile libraries argument raises an error"""
    with pytest.raises(ValueError):
        CryticCompile(
            Path(TEST_DIR / "library_linking.sol").as_posix(),
            compile_libraries="(NeedsLinkingA, 0x)",
        )
