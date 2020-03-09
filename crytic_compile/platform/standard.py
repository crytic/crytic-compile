"""
Standard crytic-compile export
"""
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Type, List, Tuple

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform import Type as PlatformType
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.utils.naming import Filename

# Cycle dependency
from crytic_compile.utils.natspec import Natspec

if TYPE_CHECKING:
    from crytic_compile import CryticCompile


def export_to_standard(crytic_compile: "CryticCompile", **kwargs: str) -> str:
    """
    Export the project to the standard crytic compile format
    :param crytic_compile:
    :param kwargs:
    :return:
    """
    # Obtain objects to represent each contract

    output = generate_standard_export(crytic_compile)

    export_dir = kwargs.get("export_dir", "crytic-export")
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    target = (
        "contracts"
        if os.path.isdir(crytic_compile.target)
        else Path(crytic_compile.target).parts[-1]
    )

    path = os.path.join(export_dir, f"{target}.json")
    with open(path, "w", encoding="utf8") as file_desc:
        json.dump(output, file_desc)

    return path


class Standard(AbstractPlatform):
    """
    Standard platform (crytic-compile specific)
    """

    NAME = "Standard"
    PROJECT_URL = "https://github.com/crytic/crytic-compile"
    TYPE = PlatformType.STANDARD

    HIDE = True

    def __init__(self, target: str, **kwargs: str):
        """
        Initializes an object which represents solc standard json

        :param target: A string path to a standard json
        """
        super().__init__(str(target), **kwargs)
        self._underlying_platform: Type[AbstractPlatform] = Standard
        self._unit_tests: List[str] = []

    def compile(self, crytic_compile: "CryticCompile", **_kwargs: str):
        """
        Compile the target (load file)

        :param crytic_compile:
        :param target:
        :param kwargs:
        :return:
        """
        from crytic_compile.crytic_compile import get_platforms

        with open(self._target, encoding="utf8") as file_desc:
            loaded_json = json.load(file_desc)
        (underlying_type, unit_tests) = load_from_compile(crytic_compile, loaded_json)
        underlying_type = PlatformType(underlying_type)
        platforms: List[Type[AbstractPlatform]] = get_platforms()
        platform = next((p for p in platforms if p.TYPE == underlying_type), Standard)
        self._underlying_platform = platform
        self._unit_tests = unit_tests

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Check if the target is the standard crytic compile export

        :param target:
        :return:
        """
        standard_ignore = kwargs.get("standard_ignore", False)
        if standard_ignore:
            return False
        if not Path(target).parts:
            return False
        return Path(target).parts[-1].endswith("_export.json")

    def is_dependency(self, path: str) -> bool:
        """
        Always return False

        :param path:
        :return:
        """
        # handled by crytic_compile_dependencies
        return False

    def _guessed_tests(self) -> List[str]:
        return self._unit_tests

    @property
    def platform_name_used(self):
        return self._underlying_platform.NAME

    @property
    def platform_project_url_used(self):
        return self._underlying_platform.PROJECT_URL

    @property
    def platform_type_used(self):
        return self._underlying_platform.TYPE


def generate_standard_export(crytic_compile: "CryticCompile") -> Dict:
    """
    Export the standard crytic compile export

    :param crytic_compile:
    :return:
    """
    contracts = dict()
    for contract_name in crytic_compile.contracts_names:
        filename = crytic_compile.filename_of_contract(contract_name)
        libraries = crytic_compile.libraries_names_and_patterns(contract_name)
        contracts[contract_name] = {
            "abi": crytic_compile.abi(contract_name),
            "bin": crytic_compile.bytecode_init(contract_name),
            "bin-runtime": crytic_compile.bytecode_runtime(contract_name),
            "srcmap": ";".join(crytic_compile.srcmap_init(contract_name)),
            "srcmap-runtime": ";".join(crytic_compile.srcmap_runtime(contract_name)),
            "filenames": {
                "absolute": filename.absolute,
                "used": filename.used,
                "short": filename.short,
                "relative": filename.relative,
            },
            "libraries": dict(libraries) if libraries else dict(),
            "is_dependency": crytic_compile.is_dependency(filename.absolute),
            "userdoc": crytic_compile.natspec[contract_name].userdoc.export(),
            "devdoc": crytic_compile.natspec[contract_name].devdoc.export(),
        }

    # Create our root object to contain the contracts and other information.

    compiler: Dict = dict()
    if crytic_compile.compiler_version:
        compiler = {
            "compiler": crytic_compile.compiler_version.compiler,
            "version": crytic_compile.compiler_version.version,
            "optimized": crytic_compile.compiler_version.optimized,
        }
    output = {
        "asts": crytic_compile.asts,
        "contracts": contracts,
        "compiler": compiler,
        "package": crytic_compile.package,
        "working_dir": str(crytic_compile.working_dir),
        "type": int(crytic_compile.platform.platform_type_used),
        "unit_tests": crytic_compile.platform.guessed_tests(),
    }
    return output


def load_from_compile(crytic_compile: "CryticCompile", loaded_json: Dict) -> Tuple[int, List[str]]:
    """
    Load from json

    :param crytic_compile:
    :param loaded_json:
    :return:
    """
    crytic_compile.package_name = loaded_json.get("package", None)
    crytic_compile.asts = loaded_json["asts"]
    crytic_compile.compiler_version = CompilerVersion(
        compiler=loaded_json["compiler"]["compiler"],
        version=loaded_json["compiler"]["version"],
        optimized=loaded_json["compiler"]["optimized"],
    )
    for contract_name, contract in loaded_json["contracts"].items():
        crytic_compile.contracts_names.add(contract_name)
        filename = Filename(
            absolute=contract["filenames"]["absolute"],
            relative=contract["filenames"]["relative"],
            short=contract["filenames"]["short"],
            used=contract["filenames"]["used"],
        )
        crytic_compile.contracts_filenames[contract_name] = filename

        crytic_compile.abis[contract_name] = contract["abi"]
        crytic_compile.bytecodes_init[contract_name] = contract["bin"]
        crytic_compile.bytecodes_runtime[contract_name] = contract["bin-runtime"]
        crytic_compile.srcmaps_init[contract_name] = contract["srcmap"].split(";")
        crytic_compile.srcmaps_runtime[contract_name] = contract["srcmap-runtime"].split(";")
        crytic_compile.libraries[contract_name] = contract["libraries"]

        userdoc = contract.get("userdoc", {})
        devdoc = contract.get("devdoc", {})
        crytic_compile.natspec[contract_name] = Natspec(userdoc, devdoc)

        if contract["is_dependency"]:
            crytic_compile.dependencies.add(filename.absolute)
            crytic_compile.dependencies.add(filename.relative)
            crytic_compile.dependencies.add(filename.short)
            crytic_compile.dependencies.add(filename.used)

    # Set our filenames
    crytic_compile.filenames = set(crytic_compile.contracts_filenames.values())

    crytic_compile.working_dir = loaded_json["working_dir"]

    return (loaded_json["type"], loaded_json["unit_tests"])


def _relative_to_short(relative):
    """

    :param relative:
    :return:
    """
    return relative
