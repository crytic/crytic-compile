"""
Test auto library linking functionality
"""
import json
import os
from pathlib import Path
import shutil

from crytic_compile.crytic_compile import CryticCompile
from crytic_compile.utils.libraries import get_deployment_order

TEST_DIR = Path(__file__).resolve().parent


def test_dependency_resolution():
    """Test that library dependencies are resolved correctly"""
    cc = CryticCompile(Path(TEST_DIR / "library_dependency_test.sol").as_posix())

    compilation_unit = list(cc.compilation_units.values())[0]
    source_unit = list(compilation_unit.source_units.values())[0]

    # Check dependencies for TestComplexDependencies
    deps = source_unit.libraries_names("TestComplexDependencies")
    assert "ComplexMath" in deps, "TestComplexDependencies should depend on ComplexMath"


def test_deployment_order():
    """Test that deployment order is calculated correctly"""
    # Create a simple dependency graph for testing
    dependencies = {
        "TestComplexDependencies": ["ComplexMath"],
        "ComplexMath": ["AdvancedMath", "MathLib"],
        "AdvancedMath": ["MathLib"],
        "MathLib": [],
        "SimpleMathContract": ["MathLib"],
    }

    target_contracts = ["TestComplexDependencies", "SimpleMathContract"]

    deployment_order, libraries_needed = get_deployment_order(dependencies, target_contracts)

    # Check that deployment order only contains libraries, not target contracts
    assert (
        "TestComplexDependencies" not in deployment_order
    ), "Target contracts should not be in deployment order"
    assert (
        "SimpleMathContract" not in deployment_order
    ), "Target contracts should not be in deployment order"

    # MathLib should come first (no dependencies)
    assert deployment_order.index("MathLib") < deployment_order.index("AdvancedMath")
    assert deployment_order.index("MathLib") < deployment_order.index("ComplexMath")
    assert deployment_order.index("AdvancedMath") < deployment_order.index("ComplexMath")

    # Check that libraries are identified correctly
    expected_libraries = {"MathLib", "AdvancedMath", "ComplexMath"}
    assert libraries_needed == expected_libraries


def test_circular_dependency_detection():
    """Test that circular dependencies are detected"""
    # Create a circular dependency graph
    dependencies = {
        "A": ["B"],
        "B": ["C"],
        "C": ["A"],  # Circular dependency
    }

    target_contracts = ["A"]

    try:
        get_deployment_order(dependencies, target_contracts)
        assert False, "Should have raised ValueError for circular dependency"
    except ValueError as e:
        assert "Circular dependency" in str(e)


def test_no_autolink_without_flag():
    """Test that autolink features don't activate without the flag"""
    cc = CryticCompile(Path(TEST_DIR / "library_dependency_test.sol").as_posix())

    # Check that autolink did not generate library addresses
    assert (
        cc.libraries is None or len(cc.libraries) == 0
    ), "Autolink should not generate library addresses without flag"

    # Export and check that no autolink file is created
    export_files = cc.export(export_format="solc", export_dir="test_no_autolink_output")

    autolink_file_found = False
    for export_file in export_files:
        filename = os.path.basename(export_file)
        if "autolink" in filename:
            autolink_file_found = True
            break

    assert not autolink_file_found, "No autolink file should be created without the flag"

    # Clean up
    if os.path.exists("test_no_autolink_output"):
        shutil.rmtree("test_no_autolink_output")


def test_autolink_functionality():
    """Test the autolink functionality"""
    cc = CryticCompile(
        Path(TEST_DIR / "library_dependency_test.sol").as_posix(), compile_autolink=True
    )

    # Check that autolink generated library addresses
    assert cc.libraries is not None, "Autolink should generate library addresses"
    assert len(cc.libraries) > 0, "Should have detected libraries to link"

    expected_libs = ["MathLib", "AdvancedMath", "ComplexMath"]
    for lib in expected_libs:
        assert lib in cc.libraries, f"Library {lib} should be auto-linked"

    # Export and check that autolink file is created
    export_files = cc.export(export_format="solc", export_dir="test_autolink_output")

    # Check that autolink file was created
    autolink_file = None
    for export_file in export_files:
        filename = os.path.basename(export_file)
        if filename.endswith(".link"):
            autolink_file = export_file
            break

    assert autolink_file is not None, "Autolink file should be created"

    with open(autolink_file, "r", encoding="utf8") as f:
        autolink_data = json.load(f)

    # Check autolink file structure
    assert "deployment_order" in autolink_data, "Autolink file should contain deployment_order"
    assert "library_addresses" in autolink_data, "Autolink file should contain library_addresses"
    assert (
        len(autolink_data["library_addresses"]) > 0
    ), "Should have library addresses in autolink file"

    # Check deployment order contains expected contracts
    deployment_order = autolink_data["deployment_order"]
    assert "MathLib" in deployment_order, "Deployment order should contain MathLib"
    assert "ComplexMath" in deployment_order, "Deployment order should contain ComplexMath"

    # Clean up
    if os.path.exists("test_autolink_output"):
        shutil.rmtree("test_autolink_output")


if __name__ == "__main__":
    test_dependency_resolution()
    test_deployment_order()
    test_circular_dependency_detection()
    test_no_autolink_without_flag()
    test_autolink_functionality()
    print("All tests passed!")
