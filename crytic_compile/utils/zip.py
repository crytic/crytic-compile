"""
Handle ZIP operations
"""
import json
from typing import List

# Cycle dependency
from typing import TYPE_CHECKING

from zipfile import ZipFile
from crytic_compile.platform.archive import generate_archive_export

if TYPE_CHECKING:
    from crytic_compile import CryticCompile


def load_from_zip(target: str) -> List["CryticCompile"]:
    """
    Load a file from a zip

    :param target:
    :return:
    """
    from crytic_compile.crytic_compile import CryticCompile

    compilations = []
    with ZipFile(target, "r") as file_desc:
        for project in file_desc.namelist():
            compilations.append(
                CryticCompile(str(file_desc.read(project)), compile_force_framework="archive")
            )

    return compilations


def save_to_zip(crytic_compiles: List["CryticCompile"], zipfile: str):
    """
    Save projects to a zip

    :param crytic_compiles:
    :param zipfile:
    :return:
    """
    with ZipFile(zipfile, "w") as file_desc:
        for crytic_compile in crytic_compiles:
            output, target_name = generate_archive_export(crytic_compile)
            file_desc.writestr(target_name, json.dumps(output))
