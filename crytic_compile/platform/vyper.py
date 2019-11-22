"""
Vyper platform
"""
import json
import os
import subprocess
from pathlib import Path

from typing import TYPE_CHECKING, Dict

from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.utils.naming import convert_filename

# Handle cycle
if TYPE_CHECKING:
    from crytic_compile import CryticCompile


def is_vyper(target: str) -> bool:
    """
    Check if the target is a vyper project
    :param target:
    :return:
    """
    return os.path.isfile(target) and target.endswith(".vy")


def compile(crytic_compile: "CryticCompile", target: str, **kwargs: str):
    """
    Compile the target
    :param crytic_compile:
    :param target:
    :param kwargs:
    :return:
    """

    crytic_compile.type = Type.VYPER

    vyper = kwargs.get("vyper", "vyper")

    targets_json = _run_vyper(target, vyper)

    assert "version" in targets_json
    crytic_compile.compiler_version = CompilerVersion(
        compiler="vyper", version=targets_json["version"], optimized=False
    )

    assert target in targets_json

    info = targets_json[target]
    contract_filename = convert_filename(target, _relative_to_short, crytic_compile)

    contract_name = Path(target).parts[-1]

    crytic_compile.contracts_names.add(contract_name)
    crytic_compile.contracts_filenames[contract_name] = contract_filename
    crytic_compile.abis[contract_name] = info["abi"]
    crytic_compile.bytecodes_init[contract_name] = info["bytecode"].replace("0x", "")
    crytic_compile.bytecodes_runtime[contract_name] = info["bytecode_runtime"].replace("0x", "")
    crytic_compile.srcmaps_init[contract_name] = []
    crytic_compile.srcmaps_runtime[contract_name] = []

    crytic_compile.filenames.add(contract_filename)

    ast = _get_vyper_ast(target, vyper)
    crytic_compile.asts[contract_filename.absolute] = ast


def _run_vyper(filename: str, vyper: str, env: Dict = None, working_dir: str = None) -> Dict:
    if not os.path.isfile(filename):
        raise InvalidCompilation(
            "{} does not exist (are you in the correct directory?)".format(filename)
        )

    cmd = [vyper, filename, "-f", "combined_json"]

    additional_kwargs = {"cwd": working_dir} if working_dir else {}
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **additional_kwargs
        )
    except Exception as exception:
        raise InvalidCompilation(exception)

    stdout, stderr = process.communicate()

    try:
        res = stdout.split(b"\n")
        res = res[-2]
        return json.loads(res)

    except json.decoder.JSONDecodeError:
        raise InvalidCompilation(f"Invalid vyper compilation\n{stderr}")


def _get_vyper_ast(filename: str, vyper: str, env=None, working_dir=None) -> Dict:
    if not os.path.isfile(filename):
        raise InvalidCompilation(
            "{} does not exist (are you in the correct directory?)".format(filename)
        )

    cmd = [vyper, filename, "-f", "ast"]

    additional_kwargs = {"cwd": working_dir} if working_dir else {}
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **additional_kwargs
        )
    except Exception as exception:
        raise InvalidCompilation(exception)

    stdout, stderr = process.communicate()

    try:
        res = stdout.split(b"\n")
        res = res[-2]
        return json.loads(res)

    except json.decoder.JSONDecodeError:
        raise InvalidCompilation(f"Invalid vyper compilation\n{stderr}")


def _relative_to_short(relative):
    return relative


def is_dependency(_path):
    """
    Always return false
    :param _path:
    :return:
    """
    return False
