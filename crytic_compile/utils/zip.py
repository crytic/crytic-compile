"""
Handle ZIP operations
"""
import json
import zipfile

# Cycle dependency
from typing import TYPE_CHECKING, List
from zipfile import ZipFile

from crytic_compile.platform.archive import generate_archive_export

if TYPE_CHECKING:
    from crytic_compile import CryticCompile


def _to_str(txt):
    if isinstance(txt, bytes):
        return txt.decode("utf8")
    return txt


def load_from_zip(target: str) -> List["CryticCompile"]:
    """
    Load a file from a zip

    :param target:
    :return:
    """
    # pylint: disable=import-outside-toplevel
    from crytic_compile.crytic_compile import CryticCompile

    compilations = []
    with ZipFile(target, "r") as file_desc:
        for project in file_desc.namelist():
            compilations.append(
                CryticCompile(_to_str(file_desc.read(project)), compile_force_framework="Archive")
            )

    return compilations


# https://docs.python.org/3/library/zipfile.html#zipfile-objects
ZIP_TYPES_ACCEPTED = {
    "lzma": zipfile.ZIP_LZMA,
    "stored": zipfile.ZIP_STORED,
    "deflated": zipfile.ZIP_DEFLATED,
    "bzip2": zipfile.ZIP_BZIP2,
}


def save_to_zip(crytic_compiles: List["CryticCompile"], zip_filename: str, zip_type: str = "lzma"):
    """
    Save projects to a zip

    :param zip_type:
    :param crytic_compiles:
    :param zip_filename:
    :return:
    """
    with ZipFile(
        zip_filename, "w", compression=ZIP_TYPES_ACCEPTED.get(zip_type, zipfile.ZIP_LZMA)
    ) as file_desc:
        for crytic_compile in crytic_compiles:
            output, target_name = generate_archive_export(crytic_compile)
            file_desc.writestr(target_name, json.dumps(output))
