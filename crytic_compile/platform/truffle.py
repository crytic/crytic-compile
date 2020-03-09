"""
Truffle platform
"""
import glob
import json
import logging
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple, List, Dict

from crytic_compile.platform.types import Type
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.utils.naming import convert_filename
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform import solc
from crytic_compile.utils.natspec import Natspec
from .abstract_platform import AbstractPlatform

# Handle cycle
if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")


def export_to_truffle(crytic_compile: "CryticCompile", **kwargs: str) -> Optional[str]:
    """
    Export to the truffle format

    :param crytic_compile:
    :param kwargs:
    :return:
    """
    # Get our export directory, if it's set, we create the path.
    export_dir = kwargs.get("export_dir", "crytic-export")
    if export_dir and not os.path.exists(export_dir):
        os.makedirs(export_dir)

    # Loop for each contract filename.
    results: List[Dict] = []
    for contract_name in crytic_compile.contracts_names:
        # Create the informational object to output for this contract
        filename = crytic_compile.contracts_filenames[contract_name]
        output = {
            "contractName": contract_name,
            "abi": crytic_compile.abi(contract_name),
            "bytecode": "0x" + crytic_compile.bytecode_init(contract_name),
            "deployedBytecode": "0x" + crytic_compile.bytecode_runtime(contract_name),
            "ast": crytic_compile.ast(filename.absolute),
            "userdoc": crytic_compile.natspec[contract_name].userdoc.export(),
            "devdoc": crytic_compile.natspec[contract_name].devdoc.export(),
        }
        results.append(output)

        # If we have an export directory, export it.

        path = os.path.join(export_dir, contract_name + ".json")
        with open(path, "w", encoding="utf8") as file_desc:
            json.dump(output, file_desc)

    return export_dir


class Truffle(AbstractPlatform):
    """
    Truffle platform
    """

    NAME = "Truffle"
    PROJECT_URL = "https://github.com/trufflesuite/truffle"
    TYPE = Type.TRUFFLE

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str):
        """
        Compile the target

        :param kwargs:
        :return:
        """

        build_directory = kwargs.get("truffle_build_directory", os.path.join("build", "contracts"))
        truffle_ignore_compile = kwargs.get("truffle_ignore_compile", False) or kwargs.get(
            "ignore_compile", False
        )
        truffle_version = kwargs.get("truffle_version", None)
        # crytic_compile.type = Type.TRUFFLE
        # Truffle on windows has naming conflicts where it will invoke truffle.js directly instead
        # of truffle.cmd (unless in powershell or git bash).
        # The cleanest solution is to explicitly call
        # truffle.cmd. Reference:
        # https://truffleframework.com/docs/truffle/reference/configuration#resolving-naming-conflicts-on-windows

        if platform.system() == "Windows":
            base_cmd = ["truffle.cmd"]
        elif kwargs.get("npx_disable", False):
            base_cmd = ["truffle"]
        else:
            base_cmd = ["npx", "truffle"]
            if truffle_version:
                if truffle_version.startswith("truffle"):
                    base_cmd = ["npx", truffle_version]
                else:
                    base_cmd = ["npx", f"truffle@{truffle_version}"]
            elif os.path.isfile(os.path.join(self._target, "package.json")):
                with open(os.path.join(self._target, "package.json"), encoding="utf8") as file_desc:
                    package = json.load(file_desc)
                    if "devDependencies" in package:
                        if "truffle" in package["devDependencies"]:
                            version = package["devDependencies"]["truffle"]
                            if version.startswith("^"):
                                version = version[1:]
                            truffle_version = "truffle@{}".format(version)
                            base_cmd = ["npx", truffle_version]
                    if "dependencies" in package:
                        if "truffle" in package["dependencies"]:
                            version = package["dependencies"]["truffle"]
                            if version.startswith("^"):
                                version = version[1:]
                            truffle_version = "truffle@{}".format(version)
                            base_cmd = ["npx", truffle_version]

        if not truffle_ignore_compile:
            cmd = base_cmd + ["compile", "--all"]

            LOGGER.info(
                "'%s' running (use --truffle-version truffle@x.x.x to use specific version)",
                " ".join(cmd),
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
        if not os.path.isdir(os.path.join(self._target, build_directory)):
            if os.path.isdir(os.path.join(self._target, "node_modules")):
                raise InvalidCompilation(
                    f"External dependencies {self._target} not found, please install them. (npm install)"
                )
            raise InvalidCompilation("`truffle compile` failed. Can you run it?")
        filenames = glob.glob(os.path.join(self._target, build_directory, "*.json"))

        optimized = None

        version = None
        compiler = None

        for filename_txt in filenames:
            with open(filename_txt, encoding="utf8") as file_desc:
                target_loaded = json.load(file_desc)

                if optimized is None:
                    if "metadata" in target_loaded:
                        metadata = target_loaded["metadata"]
                        try:
                            metadata = json.loads(metadata)
                            if "settings" in metadata:
                                if "optimizer" in metadata["settings"]:
                                    if "enabled" in metadata["settings"]["optimizer"]:
                                        optimized = metadata["settings"]["optimizer"]["enabled"]
                        except json.decoder.JSONDecodeError:
                            pass

                userdoc = target_loaded.get("userdoc", {})
                devdoc = target_loaded.get("devdoc", {})
                natspec = Natspec(userdoc, devdoc)

                if not "ast" in target_loaded:
                    continue

                filename = target_loaded["ast"]["absolutePath"]
                filename = convert_filename(
                    filename, _relative_to_short, crytic_compile, working_dir=self._target
                )

                crytic_compile.asts[filename.absolute] = target_loaded["ast"]
                crytic_compile.filenames.add(filename)
                contract_name = target_loaded["contractName"]
                crytic_compile.natspec[contract_name] = natspec
                crytic_compile.contracts_filenames[contract_name] = filename
                crytic_compile.contracts_names.add(contract_name)
                crytic_compile.abis[contract_name] = target_loaded["abi"]
                crytic_compile.bytecodes_init[contract_name] = target_loaded["bytecode"].replace(
                    "0x", ""
                )
                crytic_compile.bytecodes_runtime[contract_name] = target_loaded[
                    "deployedBytecode"
                ].replace("0x", "")
                crytic_compile.srcmaps_init[contract_name] = target_loaded["sourceMap"].split(";")
                crytic_compile.srcmaps_runtime[contract_name] = target_loaded[
                    "deployedSourceMap"
                ].split(";")

                if compiler is None:
                    compiler = target_loaded.get("compiler", {}).get("name", None)
                if version is None:
                    version = target_loaded.get("compiler", {}).get("version", None)
                    if "+" in version:
                        version = version[0 : version.find("+")]

        if version is None or compiler is None:
            version_from_config = _get_version_from_config(self._target)
            if version_from_config:
                version, compiler = version_from_config
            else:
                version, compiler = _get_version(base_cmd, cwd=self._target)

        crytic_compile.compiler_version = CompilerVersion(
            compiler=compiler, version=version, optimized=optimized
        )

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Check if the target is a truffle project

        :param target:
        :return:
        """
        truffle_ignore = kwargs.get("truffle_ignore", False)
        if truffle_ignore:
            return False
        return os.path.isfile(os.path.join(target, "truffle.js")) or os.path.isfile(
            os.path.join(target, "truffle-config.js")
        )

    def is_dependency(self, path: str) -> bool:
        """
        Check if the target is a dependency

        :param path:
        :return:
        """
        return "node_modules" in Path(path).parts

    def _guessed_tests(self) -> List[str]:
        """
        Guess the potential unit tests commands

        :return:
        """
        return ["truffle test"]


def _get_version_from_config(target: str) -> Optional[Tuple[str, str]]:
    """
    Naive check on the truffleconfig file to get the version

    :param target:
    :return: (version, compiler) | None
    """
    config = Path(target, "truffle-config.js")
    if not config.exists():
        config = Path(target, "truffle.js")
        if not config.exists():
            return None
    with open(config) as config_f:
        config_buffer = config_f.read()

    # The config is a javascript file
    # Use a naive regex to match the solc version
    match = re.search(r'solc: {[ ]*\n[ ]*version: "([0-9\.]*)', config_buffer)
    if match:
        if match.groups():
            version = match.groups()[0]
            return version, "solc-js"
    return None


def _get_version(truffle_call, cwd):
    cmd = truffle_call + ["version"]
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    except OSError as error:
        raise InvalidCompilation(f"Truffle failed: {error}")
    stdout, _ = process.communicate()
    stdout = stdout.decode()  # convert bytestrings to unicode strings
    if not stdout:
        raise InvalidCompilation(f"Truffle failed to run: 'truffle version'")
    stdout = stdout.split("\n")
    for line in stdout:
        if "Solidity" in line:
            if "native" in line:
                return solc.get_version("solc"), "solc-native"
            version = re.findall(r"\d+\.\d+\.\d+", line)[0]
            compiler = re.findall(r"(solc[a-z\-]*)", line)
            if len(compiler) > 0:
                return version, compiler

    raise InvalidCompilation(f"Solidity version not found {stdout}")


def _relative_to_short(relative):
    short = relative
    try:
        short = short.relative_to(Path("contracts"))
    except ValueError:
        try:
            short = short.relative_to("node_modules")
        except ValueError:
            pass
    return short
