"""
Archive platform.
"""
import os
import json
from typing import Dict, Tuple, TYPE_CHECKING
from pathlib import Path
from crytic_compile.platform import standard

# Cycle dependency
if TYPE_CHECKING:
    from crytic_compile import CryticCompile


def is_archive(target: str) -> bool:
    """
    Check if the target is an archive
    :param target:
    :return:
    """
    if not Path(target).parts:
        return False
    return Path(target).parts[-1].endswith("_export_archive.json")


def compile(crytic_compile: "CryticCompile", target: str, **_kwargs):
    """
    Compile
    :param crytic_compile:
    :param target:
    :param _kwargs:
    :return:
    """
    if isinstance(target, str) and os.path.isfile(target):
        with open(target, encoding="utf8") as f_target:
            loaded_json = json.load(f_target)
    else:
        loaded_json = json.loads(target)
    standard.load_from_compile(crytic_compile, loaded_json)

    crytic_compile.src_content = loaded_json["source_content"]


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


def export(crytic_compile: "CryticCompile", **kwargs):
    """
    Export the archive
    :param crytic_compile:
    :param kwargs:
    :return:
    """
    # Obtain objects to represent each contract

    output, target = generate_archive_export(crytic_compile)

    export_dir = kwargs.get("export_dir", "crytic-compile")
    if export_dir:
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        path = os.path.join(export_dir, target)
        with open(path, "w", encoding="utf8") as f_path:
            json.dump(output, f_path)

        return path
    return None


def is_dependency(_path: str) -> bool:
    """
    Check if the _path is a dependency. Always false
    :param _path:
    :return:
    """
    # handled by crytic_compile_dependencies
    return False


def _relative_to_short(relative: Path) -> Path:
    """
    Translate relative path to short. Return the same
    :param relative:
    :return:
    """
    return relative
