"""
Standard crytic-compile export
"""
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Type, List, Tuple

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform import Type as PlatformType
from crytic_compile.platform.standard import generate_standard_export
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.utils.naming import Filename

# Cycle dependency
from crytic_compile.utils.natspec import Natspec

if TYPE_CHECKING:
    from crytic_compile import CryticCompile


def export_to_raw_files(crytic_compile: "CryticCompile", **kwargs: str) -> str:
    """
    Export the project to the raw compile format
    :param crytic_compile:
    :param kwargs:
    :return:
    """
    # Obtain objects to represent each contract

    output = generate_standard_export(crytic_compile)

    export_dir = kwargs.get("export_dir", "crytic-export")
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    for contract in output["contracts"]:
        path = os.path.join(export_dir, f"{contract}.abi")
        with open(path, "w", encoding="utf8") as file_desc:
            json.dump(output["contracts"][contract]["abi"], file_desc)

        path = os.path.join(export_dir, f"{contract}.bin")
        with open(path, "w", encoding="utf8") as file_desc:
            file_desc.write(output["contracts"][contract]["bin"])

    return path


class Raw(AbstractPlatform):
    """
    Raw platform (only bytecode and abi)
    """

    NAME = "Raw"
    PROJECT_URL = "https://github.com/crytic/crytic-compile"
    TYPE = PlatformType.RAW

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
