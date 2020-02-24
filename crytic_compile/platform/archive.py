"""
Archive platform.
It is similar to the standard platform, except that the file generated
contains a "source_content" field
Which is a map: filename -> sourcecode
"""
import os
import json
from typing import Dict, Tuple, TYPE_CHECKING
from pathlib import Path
from crytic_compile.platform import standard, Type

# Cycle dependency
from crytic_compile.platform.abstract_platform import AbstractPlatform

if TYPE_CHECKING:
    from crytic_compile import CryticCompile


def export_to_archive(crytic_compile: "CryticCompile", **kwargs) -> str:
    """
    Export the archive
    :param crytic_compile:
    :param kwargs:
    :return:
    """
    # Obtain objects to represent each contract

    output, target = generate_archive_export(crytic_compile)

    export_dir = kwargs.get("export_dir", "crytic-export")

    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    path = os.path.join(export_dir, target)
    with open(path, "w", encoding="utf8") as f_path:
        json.dump(output, f_path)

    return path


class Archive(AbstractPlatform):
    """
    Archive platform. It is similar to the Standard platform, but contains also the source code
    """

    NAME = "Archive"
    PROJECT_URL = "https://github.com/crytic/crytic-compile"
    TYPE = Type.ARCHIVE

    HIDE = True

    def __init__(self, target: str, **kwargs: str):
        """
        Initializes an object which represents solc standard json
        :param target: A string path to a standard json
        """
        super().__init__(str(target), **kwargs)
        self._underlying_type = Type.ARCHIVE

    def compile(self, crytic_compile: "CryticCompile", **_kwargs):
        """
        Compile
        :param crytic_compile:
        :param _kwargs:
        :return:
        """
        if isinstance(self._target, str) and os.path.isfile(self._target):
            with open(self._target, encoding="utf8") as f_target:
                loaded_json = json.load(f_target)
        else:
            loaded_json = json.loads(self._target)
        underlying_type = standard.load_from_compile(crytic_compile, loaded_json)
        self._underlying_type = Type(underlying_type)

        crytic_compile.src_content = loaded_json["source_content"]

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Check if the target is an archive
        :param target:
        :return:
        """
        archive_ignore = kwargs.get("standard_ignore", False)
        if archive_ignore:
            return False
        if not Path(target).parts:
            return False
        return Path(target).parts[-1].endswith("_export_archive.json")

    def is_dependency(self, _path: str) -> bool:
        """
        Check if the _path is a dependency. Always false
        :param _path:
        :return:
        """
        # TODO: check if its correctly handled by crytic_compile_dependencies
        return False


def generate_archive_export(crytic_compile: "CryticCompile") -> Tuple[Dict, str]:
    """
    Generate the archive export
    :param crytic_compile:
    :return:
    """
    output = standard.generate_standard_export(crytic_compile)
    output["source_content"] = crytic_compile.src_content

    target = crytic_compile.target
    target = "contracts" if os.path.isdir(target) else Path(target).parts[-1]
    target = f"{target}_export_archive.json"

    return output, target


def _relative_to_short(relative: Path) -> Path:
    """
    Translate relative path to short. Return the same
    :param relative:
    :return:
    """
    return relative
