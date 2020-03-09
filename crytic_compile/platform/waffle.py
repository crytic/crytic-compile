"""
Waffle platform
"""

import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import convert_filename

# Handle cycle
from crytic_compile.utils.natspec import Natspec

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")


class Waffle(AbstractPlatform):
    """
    Waffle platform
    """

    NAME = "Waffle"
    PROJECT_URL = "https://github.com/EthWorks/Waffle"
    TYPE = Type.WAFFLE

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str):
        """
        Compile the target

        :param crytic_compile:
        :param target:
        :param kwargs:
        :return:
        """

        waffle_ignore_compile = kwargs.get("waffle_ignore_compile", False) or kwargs.get(
            "ignore_compile", False
        )
        target = self._target

        cmd = ["waffle"]
        if not kwargs.get("npx_disable", False):
            cmd = ["npx"] + cmd

        # Default behaviour (without any config_file)
        build_directory = os.path.join("build")
        compiler = "native"
        version = _get_version(compiler, target)
        config: Dict = dict()

        config_file = kwargs.get("waffle_config_file", None)

        # Read config file
        if config_file:
            config = _load_config(config_file)
            version = _get_version(compiler, target, config=config)

            if "targetPath" in config:
                build_directory = config["targetPath"]

            if "compiler" in config:
                compiler = config["compiler"]

        if "outputType" not in config or config["outputType"] != "all":
            config["outputType"] = "all"

        needed_config = {
            "compilerOptions": {
                "outputSelection": {
                    "*": {
                        "*": [
                            "evm.bytecode.object",
                            "evm.deployedBytecode.object",
                            "abi",
                            "evm.bytecode.sourceMap",
                            "evm.deployedBytecode.sourceMap",
                        ],
                        "": ["ast"],
                    }
                }
            }
        }

        # Set the config as it should be
        if "compilerOptions" in config:
            curr_config: Dict = config["compilerOptions"]
            curr_needed_config: Dict = needed_config["compilerOptions"]
            if "outputSelection" in curr_config:
                curr_config = curr_config["outputSelection"]
                curr_needed_config = curr_needed_config["outputSelection"]
                if "*" in curr_config:
                    curr_config = curr_config["*"]
                    curr_needed_config = curr_needed_config["*"]
                    if "*" in curr_config:
                        curr_config["*"] += curr_needed_config["*"]
                    else:
                        curr_config["*"] = curr_needed_config["*"]

                    if "" in curr_config:
                        curr_config[""] += curr_needed_config[""]
                    else:
                        curr_config[""] = curr_needed_config[""]

                else:
                    curr_config["*"] = curr_needed_config["*"]

            else:
                curr_config["outputSelection"] = curr_needed_config["outputSelection"]
        else:
            config["compilerOptions"] = needed_config["compilerOptions"]

        if not waffle_ignore_compile:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as file_desc:
                json.dump(config, file_desc)
                file_desc.flush()

                cmd += [os.path.relpath(file_desc.name)]

                LOGGER.info("Temporary file created: %s", file_desc.name)
                LOGGER.info("'%s running", " ".join(cmd))

                try:
                    process = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=target
                    )
                except OSError as error:
                    raise InvalidCompilation(error)

                stdout, stderr = process.communicate()
                if stdout:
                    LOGGER.info(stdout.decode())
                if stderr:
                    LOGGER.error(stderr.decode())

        if not os.path.isdir(os.path.join(target, build_directory)):
            raise InvalidCompilation("`waffle` compilation failed: build directory not found")

        combined_path = os.path.join(target, build_directory, "Combined-Json.json")
        if not os.path.exists(combined_path):
            raise InvalidCompilation("`Combined-Json.json` not found")

        with open(combined_path, "r") as file_desc:
            target_all = json.load(file_desc)

        optimized = None

        for contract in target_all["contracts"]:
            target_loaded = target_all["contracts"][contract]
            contract = contract.split(":")
            filename_rel = os.path.join(target, contract[0])
            filename = convert_filename(
                filename_rel, _relative_to_short, crytic_compile, working_dir=target
            )

            contract_name = contract[1]

            crytic_compile.asts[filename.absolute] = target_all["sources"][contract[0]]["AST"]
            crytic_compile.filenames.add(filename)
            crytic_compile.contracts_filenames[contract_name] = filename
            crytic_compile.contracts_names.add(contract_name)
            crytic_compile.abis[contract_name] = target_loaded["abi"]

            userdoc = target_loaded.get("userdoc", {})
            devdoc = target_loaded.get("devdoc", {})
            natspec = Natspec(userdoc, devdoc)
            crytic_compile.natspec[contract_name] = natspec

            crytic_compile.bytecodes_init[contract_name] = target_loaded["evm"]["bytecode"][
                "object"
            ]
            crytic_compile.srcmaps_init[contract_name] = target_loaded["evm"]["bytecode"][
                "sourceMap"
            ].split(";")
            crytic_compile.bytecodes_runtime[contract_name] = target_loaded["evm"][
                "deployedBytecode"
            ]["object"]
            crytic_compile.srcmaps_runtime[contract_name] = target_loaded["evm"][
                "deployedBytecode"
            ]["sourceMap"].split(";")

        crytic_compile.compiler_version = CompilerVersion(
            compiler=compiler, version=version, optimized=optimized
        )

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Check if the target is a waffle project

        :param target:
        :return:
        """
        waffle_ignore = kwargs.get("waffle_ignore", False)
        if waffle_ignore:
            return False
        if os.path.isfile(os.path.join(target, "package.json")):
            with open("package.json", encoding="utf8") as file_desc:
                package = json.load(file_desc)
            if "dependencies" in package:
                return "ethereum-waffle" in package["dependencies"]
        return False

    def is_dependency(self, path: str) -> bool:
        """
        Check if the path is a dependency

        :param path:
        :return:
        """
        return "node_modules" in Path(path).parts

    def _guessed_tests(self) -> List[str]:
        """
        Guess the potential unit tests commands

        :return:
        """
        return ["npx mocha"]


def _load_config(config_file: str) -> Dict:
    """
    Load the config file

    :param config_file:
    :return:
    """
    with open(config_file, "r") as file_desc:
        content = file_desc.read()

    if "module.exports" in content:
        raise InvalidCompilation("module.export to supported for waffle")
    return json.loads(content)


def _get_version(compiler: str, cwd: str, config=None) -> str:
    version = ""
    if config is not None and "solcVersion" in config:
        version = re.findall(r"\d+\.\d+\.\d+", config["solcVersion"])[0]

    elif compiler == "dockerized-solc":
        version = config["docker-tag"]

    elif compiler == "native":
        cmd = ["solc", "--version"]
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        except OSError as error:
            raise InvalidCompilation(error)
        stdout_bytes, _ = process.communicate()
        stdout_txt = stdout_bytes.decode()  # convert bytestrings to unicode strings
        stdout = stdout_txt.split("\n")
        for line in stdout:
            if "Version" in line:
                version = re.findall(r"\d+\.\d+\.\d+", line)[0]

    elif compiler == "solc-js":
        cmd = ["solcjs", "--version"]
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        except OSError as error:
            raise InvalidCompilation(error)
        stdout_bytes, _ = process.communicate()
        stdout_txt = stdout_bytes.decode()  # convert bytestrings to unicode strings
        version = re.findall(r"\d+\.\d+\.\d+", stdout_txt)[0]

    else:
        raise InvalidCompilation(f"Solidity version not found {compiler}")

    return version


def _relative_to_short(relative: Path) -> Path:
    short = relative
    try:
        short = short.relative_to(Path("contracts"))
    except ValueError:
        try:
            short = short.relative_to("node_modules")
        except ValueError:
            pass
    return short
