"""
Builder platform
"""
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, List, Tuple

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import convert_filename, extract_name
from crytic_compile.utils.natspec import Natspec
from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.contract import Contract
from crytic_compile.source_unit import SourceUnit
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
    def compile(self, crytic_compile: "CryticCompile", **kwargs: str) -> None:
        """Run the compilation

        Args:
            crytic_compile (CryticCompile): Associated CryticCompile objects
            **kwargs: optional arguments. Used: "buidler_cache_directory", "buidler_ignore_compile", "ignore_compile",
                "buidler_working_dir", "buidler_skip_directory_name_fix", "npx_disable"

        Raises:
            InvalidCompilation: If buidler failed to run
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
                "'%s' running",
                " ".join(cmd),
            )

            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self._target,
                executable=shutil.which(cmd[0]),
            ) as process:

                stdout_bytes, stderr_bytes = process.communicate()
                stdout, stderr = (
                    stdout_bytes.decode(errors="backslashreplace"),
                    stderr_bytes.decode(errors="backslashreplace"),
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

        compilation_unit = CompilationUnit(crytic_compile, str(target_solc_file))
        crytic_compile.compilation_units[compilation_unit.unique_id] = compilation_unit

        (compiler, version_from_config, optimized) = _get_version_from_config(Path(cache_directory))

        compilation_unit.compiler_version = CompilerVersion(
            compiler=compiler, version=version_from_config, optimized=optimized
        )

        skip_filename = compilation_unit.compiler_version.version in [
            f"0.4.{x}" for x in range(0, 10)
        ]
        
        with open(target_solc_file, encoding="utf8") as file_desc:
            targets_json = json.load(file_desc)
            
            if "sources" not in targets_json or "contracts" not in targets_json:
                LOGGER.error(
                    "Some error"
                )
                raise InvalidCompilation(
                    f"Incorrect json file generated"
                )
            
            for path, info in targets_json["sources"].items():
                if path.startswith("ontracts/") and not skip_directory_name_fix:
                    path = "c" + path

                if skip_filename:
                    filename = convert_filename(
                        self._target,
                        relative_to_short,
                        crytic_compile,
                        working_dir=buidler_working_dir,
                    )
                else:
                    filename = convert_filename(
                        path, relative_to_short, crytic_compile, working_dir=buidler_working_dir
                    )
                
                ast = info["ast"]
                source_unit = SourceUnit(compilation_unit, filename, ast)
                compilation_unit.source_units[filename] = source_unit
            
            for original_filename, contracts_info in targets_json["contracts"].items():
                filename = convert_filename(
                    original_filename,
                    relative_to_short,
                    crytic_compile,
                    working_dir=buidler_working_dir,
                )
                source_unit = compilation_unit.source_units[filename]

                for original_contract_name, info in contracts_info.items():
                    if (
                        original_filename.startswith("ontracts/")
                        and not skip_directory_name_fix
                    ):
                        original_filename = "c" + original_filename
                    
                    contract_name = extract_name(original_contract_name)
                    abi = info["abi"]
                    init_bytecode = info["evm"]["bytecode"]["object"].replace("0x", "")
                    runtime_bytecode = info["evm"]["deployedBytecode"]["object"].replace("0x", "")
                    srcmap_init = info["evm"]["bytecode"][ "sourceMap"]
                    srcmap_runtime = info["evm"]["deployedBytecode"]["sourceMap"]
                    userdoc = info.get("userdoc", {})
                    devdoc = info.get("devdoc", {})
                    natspec = Natspec(userdoc, devdoc)
                    contract = Contract(source_unit, contract_name, abi, init_bytecode, runtime_bytecode, srcmap_init, srcmap_runtime, natspec)
                    source_unit.contracts[contract_name] = contract


    def clean(self, **kwargs: str) -> None:
        # TODO: call "buldler clean"?
        pass

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """Check if the target is a buidler project

        Args:
            target (str): path to the target
            **kwargs: optional arguments. Used: "buidler_ignore"

        Returns:
            bool: True if the target is a buidler project
        """
        buidler_ignore = kwargs.get("buidler_ignore", False)
        if buidler_ignore:
            return False
        is_javascript = os.path.isfile(os.path.join(target, "buidler.config.js"))
        is_typescript = os.path.isfile(os.path.join(target, "buidler.config.ts"))
        return is_javascript or is_typescript

    def is_dependency(self, path: str) -> bool:
        """Check if the path is a dependency

        Args:
            path (str): path to the target

        Returns:
            bool: True if the target is a dependency
        """
        if path in self._cached_dependencies:
            return self._cached_dependencies[path]
        ret = "node_modules" in Path(path).parts
        self._cached_dependencies[path] = ret
        return ret

    def _guessed_tests(self) -> List[str]:
        """Guess the potential unit tests commands

        Returns:
            List[str]: The guessed unit tests commands
        """
        return ["buidler test"]


def _get_version_from_config(builder_directory: Path) -> Tuple[str, str, bool]:
    """Parse the compiler version

    Args:
        builder_directory (Path): path to the project's directory

    Raises:
        InvalidCompilation: If the configuration file was not found

    Returns:
        Tuple[str, str, bool]: (compiler_name,compiler_version,is_optimized)
    """

    #    :return: (version, optimized)

    path_config = Path(builder_directory, "last-solc-config.json")
    if not path_config.exists():
        path_config = Path(builder_directory, "last-vyper-config.json")
        if not path_config.exists():
            raise InvalidCompilation(f"{path_config} not found")
        with open(path_config, "r", encoding="utf8") as config_f:
            version = config_f.read()
            return "vyper", version, False
    with open(path_config, "r", encoding="utf8") as config_f:
        config = json.load(config_f)

    version = config["solc"]["version"]

    optimized = "optimizer" in config["solc"] and config["solc"]["optimizer"]
    return "solc", version, optimized
