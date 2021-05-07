"""
Vyper platform
"""
import json
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List

from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import convert_filename

# Handle cycle
from crytic_compile.utils.natspec import Natspec

if TYPE_CHECKING:
    from crytic_compile import CryticCompile


class Vyper(AbstractPlatform):
    """
    Vyper platform
    """

    NAME = "vyper"
    PROJECT_URL = "https://github.com/vyperlang/vyper"
    TYPE = Type.VYPER

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str):
        """
        Compile the target

        :param crytic_compile:
        :param target:
        :param kwargs:
        :return:
        """

        target = self._target

        vyper = kwargs.get("vyper", "vyper")

        targets_json = _run_vyper(target, vyper)

        assert "version" in targets_json
        compilation_unit = CompilationUnit(crytic_compile, str(target))

        compilation_unit.compiler_version = CompilerVersion(
            compiler="vyper", version=targets_json["version"], optimized=False
        )

        assert target in targets_json

        info = targets_json[target]
        contract_filename = convert_filename(target, _relative_to_short, crytic_compile)

        contract_name = Path(target).parts[-1]

        compilation_unit.contracts_names.add(contract_name)
        compilation_unit.contracts_filenames[contract_name] = contract_filename
        compilation_unit.abis[contract_name] = info["abi"]
        compilation_unit.bytecodes_init[contract_name] = info["bytecode"].replace("0x", "")
        compilation_unit.bytecodes_runtime[contract_name] = info["bytecode_runtime"].replace(
            "0x", ""
        )
        # Vyper does not provide the source mapping for the init bytecode
        compilation_unit.srcmaps_init[contract_name] = []
        # info["source_map"]["pc_pos_map"] contains the source mapping in a simpler format
        # However pc_pos_map_compressed" seems to follow solc's format, so for convenience
        # We store the same
        # TODO: create SourceMapping class, so that srcmaps_runtime would store an class
        # That will give more flexebility to different compilers
        compilation_unit.srcmaps_runtime[contract_name] = info["source_map"][
            "pc_pos_map_compressed"
        ]

        crytic_compile.filenames.add(contract_filename)

        # Natspec not yet handled for vyper
        compilation_unit.natspec[contract_name] = Natspec({}, {})

        ast = _get_vyper_ast(target, vyper)
        compilation_unit.asts[contract_filename.absolute] = ast

    def is_dependency(self, _path):
        """
        Always return false

        :param _path:
        :return:
        """
        return False

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Check if the target is a vyper project

        :param target:
        :return:
        """
        vyper_ignore = kwargs.get("vyper_ignore", False)
        if vyper_ignore:
            return False
        return os.path.isfile(target) and target.endswith(".vy")

    def _guessed_tests(self) -> List[str]:
        """
        Guess the potential unit tests commands

        :return:
        """
        return []


def _run_vyper(filename: str, vyper: str, env: Dict = None, working_dir: str = None) -> Dict:
    if not os.path.isfile(filename):
        raise InvalidCompilation(
            "{} does not exist (are you in the correct directory?)".format(filename)
        )

    cmd = [vyper, filename, "-f", "combined_json"]

    additional_kwargs: Dict = {"cwd": working_dir} if working_dir else {}
    try:
        with subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **additional_kwargs
        ) as process:
            stdout, stderr = process.communicate()
            res = stdout.split(b"\n")
            res = res[-2]
            return json.loads(res)
    except OSError as error:
        # pylint: disable=raise-missing-from
        raise InvalidCompilation(error)
    except json.decoder.JSONDecodeError:
        # pylint: disable=raise-missing-from
        raise InvalidCompilation(f"Invalid vyper compilation\n{stderr}")


def _get_vyper_ast(filename: str, vyper: str, env=None, working_dir=None) -> Dict:
    if not os.path.isfile(filename):
        raise InvalidCompilation(
            "{} does not exist (are you in the correct directory?)".format(filename)
        )

    cmd = [vyper, filename, "-f", "ast"]

    additional_kwargs = {"cwd": working_dir} if working_dir else {}
    try:
        with subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **additional_kwargs
        ) as process:
            stdout, stderr = process.communicate()
            res = stdout.split(b"\n")
            res = res[-2]
            return json.loads(res)
    except json.decoder.JSONDecodeError:
        # pylint: disable=raise-missing-from
        raise InvalidCompilation(f"Invalid vyper compilation\n{stderr}")
    except Exception as exception:
        # pylint: disable=raise-missing-from
        raise InvalidCompilation(exception)


def _relative_to_short(relative):
    return relative
