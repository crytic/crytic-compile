"""
Standard crytic-compile export
"""
import json
import os
from pathlib import Path


from typing import TYPE_CHECKING, Dict, Optional
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.utils.naming import Filename

# Cycle dependency
if TYPE_CHECKING:
    from crytic_compile import CryticCompile


def is_standard(target: str) -> bool:
    """
    Check if the target is the standard crytic compile export
    :param target:
    :return:
    """
    if not Path(target).parts:
        return False
    return Path(target).parts[-1].endswith("_export.json")


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
        "type": int(crytic_compile.type),
    }
    return output


def export(crytic_compile: "CryticCompile", **kwargs: str) -> Optional[str]:
    """
    Export the project to the standard crytic compile format
    :param crytic_compile:
    :param kwargs:
    :return:
    """
    # Obtain objects to represent each contract

    output = generate_standard_export(crytic_compile)

    export_dir = kwargs.get("export_dir", "crytic-compile")
    if export_dir:
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        target = crytic_compile.target
        if isinstance(target, str):
            target = "contracts" if os.path.isdir(target) else Path(target).parts[-1]

            path = os.path.join(export_dir, f"{target}.json")
            with open(path, "w", encoding="utf8") as file_desc:
                json.dump(output, file_desc)

            return path
    return None


def compile(crytic_compile: "CryticCompile", target: str, **_kwargs: str):
    """
    Compile the target (load file)
    :param crytic_compile:
    :param target:
    :param kwargs:
    :return:
    """
    with open(target, encoding="utf8") as file_desc:
        loaded_json = json.load(file_desc)
    load_from_compile(crytic_compile, loaded_json)


def load_from_compile(crytic_compile: "CryticCompile", loaded_json: Dict):
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

        if contract["is_dependency"]:
            crytic_compile.dependencies.add(filename.absolute)
            crytic_compile.dependencies.add(filename.relative)
            crytic_compile.dependencies.add(filename.short)
            crytic_compile.dependencies.add(filename.used)

    # Set our filenames
    crytic_compile.filenames = set(crytic_compile.contracts_filenames.values())

    crytic_compile.working_dir = loaded_json["working_dir"]
    crytic_compile.type = loaded_json["type"]


def is_dependency(filename: str) -> bool:
    """
    Always return False
    :param filename:
    :return:
    """
    # handled by crytic_compile_dependencies
    return False


def _relative_to_short(relative):
    """

    :param relative:
    :return:
    """
    return relative
