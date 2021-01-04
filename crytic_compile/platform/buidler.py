"""
Builder platform
"""
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import convert_filename, extract_name
from crytic_compile.utils.natspec import Natspec

from .abstract_platform import AbstractPlatform

# Handle cycle
from .solc import relative_to_short

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")


class Buidler(AbstractPlatform):
    """
    Builder platform
    """

    NAME = "Buidler"
    PROJECT_URL = "https://github.com/nomiclabs/buidler"
    TYPE = Type.BUILDER

    # pylint: disable=too-many-locals,too-many-statements,too-many-branches
    def compile(self, crytic_compile: "CryticCompile", **kwargs: str):
        """
        Compile the target

        :param kwargs:
        :return:
        """

        cache_directory = kwargs.get("buidler_cache_directory", "")
        target_solc_file = os.path.join(cache_directory, "solc-output.json")
        target_vyper_file = os.path.join(cache_directory, "vyper-docker-updates.json")
        buidler_ignore_compile = kwargs.get("buidler_ignore_compile", False) or kwargs.get(
            "ignore_compile", False
        )
        buidler_working_dir = kwargs.get("buidler_working_dir", None)
        # See https://github.com/crytic/crytic-compile/issues/116
        skip_directory_name_fix = kwargs.get("buidler_skip_directory_name_fix", False)

        base_cmd = ["buidler"]
        if not kwargs.get("npx_disable", False):
            base_cmd = ["npx"] + base_cmd

        if not buidler_ignore_compile:
            cmd = base_cmd + ["compile"]

            LOGGER.info(
                "'%s' running", " ".join(cmd),
            )

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self._target
            )

            stdout_bytes, stderr_bytes = process.communicate()
            stdout, stderr = (
                stdout_bytes.decode(),
                stderr_bytes.decode(),
            )  # convert bytestrings to unicode strings

            LOGGER.info(stdout)
            if stderr:
                LOGGER.error(stderr)

        if not os.path.isfile(os.path.join(self._target, target_solc_file)):
            if os.path.isfile(os.path.join(self._target, target_vyper_file)):
                txt = "Vyper not yet supported with buidler."
                txt += " Please open an issue in https://github.com/crytic/crytic-compile"
                raise InvalidCompilation(txt)
            txt = f"`buidler compile` failed. Can you run it?\n{os.path.join(self._target, target_solc_file)} not found"
            raise InvalidCompilation(txt)

        (compiler, version_from_config, optimized) = _get_version_from_config(cache_directory)

        crytic_compile.compiler_version = CompilerVersion(
            compiler=compiler, version=version_from_config, optimized=optimized
        )

        skip_filename = crytic_compile.compiler_version.version in [
            f"0.4.{x}" for x in range(0, 10)
        ]

        with open(target_solc_file, encoding="utf8") as file_desc:
            targets_json = json.load(file_desc)

            if "contracts" in targets_json:
                for original_filename, contracts_info in targets_json["contracts"].items():
                    for original_contract_name, info in contracts_info.items():
                        contract_name = extract_name(original_contract_name)

                        if (
                            original_filename.startswith("ontracts/")
                            and not skip_directory_name_fix
                        ):
                            original_filename = "c" + original_filename

                        contract_filename = convert_filename(
                            original_filename,
                            relative_to_short,
                            crytic_compile,
                            working_dir=buidler_working_dir,
                        )

                        crytic_compile.contracts_names.add(contract_name)
                        crytic_compile.contracts_filenames[contract_name] = contract_filename

                        crytic_compile.abis[contract_name] = info["abi"]
                        crytic_compile.bytecodes_init[contract_name] = info["evm"]["bytecode"][
                            "object"
                        ]
                        crytic_compile.bytecodes_runtime[contract_name] = info["evm"][
                            "deployedBytecode"
                        ]["object"]
                        crytic_compile.srcmaps_init[contract_name] = info["evm"]["bytecode"][
                            "sourceMap"
                        ].split(";")
                        crytic_compile.srcmaps_runtime[contract_name] = info["evm"][
                            "deployedBytecode"
                        ]["sourceMap"].split(";")
                        userdoc = info.get("userdoc", {})
                        devdoc = info.get("devdoc", {})
                        natspec = Natspec(userdoc, devdoc)
                        crytic_compile.natspec[contract_name] = natspec

            if "sources" in targets_json:
                for path, info in targets_json["sources"].items():

                    if path.startswith("ontracts/") and not skip_directory_name_fix:
                        path = "c" + path

                    if skip_filename:
                        path = convert_filename(
                            self._target,
                            relative_to_short,
                            crytic_compile,
                            working_dir=buidler_working_dir,
                        )
                    else:
                        path = convert_filename(
                            path, relative_to_short, crytic_compile, working_dir=buidler_working_dir
                        )
                    crytic_compile.filenames.add(path)
                    crytic_compile.asts[path.absolute] = info["ast"]

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Check if the target is a buidler project

        :param target:
        :return:
        """
        buidler_ignore = kwargs.get("buidler_ignore", False)
        if buidler_ignore:
            return False
        is_javascript = os.path.isfile(os.path.join(target, "buidler.config.js"))
        is_typescript = os.path.isfile(os.path.join(target, "buidler.config.ts"))
        return is_javascript or is_typescript

    def is_dependency(self, path: str) -> bool:
        """
        Check if the target is a dependency

        :param path:
        :return:
        """
        if path in self._cached_dependencies:
            return self._cached_dependencies[path]
        ret = "node_modules" in Path(path).parts
        self._cached_dependencies[path] = ret
        return ret

    def _guessed_tests(self) -> List[str]:
        """
        Guess the potential unit tests commands

        :return:
        """
        return ["buidler test"]


def _get_version_from_config(builder_directory: Path) -> Optional[Tuple[str, str, bool]]:
    """
    :return: (version, optimized)
    """
    config = Path(builder_directory, "last-solc-config.json")
    if not config.exists():
        config = Path(builder_directory, "last-vyper-config.json")
        if not config.exists():
            raise InvalidCompilation(f"{config} not found")
        with open(config) as config_f:
            version = config_f.read()
            return "vyper", version, False
    with open(config) as config_f:
        config = json.load(config_f)

    version = config["solc"]["version"]

    optimized = "optimizer" in config["solc"] and config["solc"]["optimizer"]
    return "solc", version, optimized
