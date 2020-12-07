"""
Truffle platform
"""
import glob
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform import solc
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type
from crytic_compile.utils.naming import convert_filename
from crytic_compile.utils.natspec import Natspec

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

    # pylint: disable=too-many-locals,too-many-statements,too-many-branches
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

        truffle_overwrite_config = kwargs.get("truffle_overwrite_config", False)

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

            config_used = None
            config_saved = None
            if truffle_overwrite_config:
                overwritten_version = kwargs.get("truffle_overwrite_version", None)
                # If the version is not provided, we try to guess it with the config file
                if overwritten_version is None:
                    version_from_config = _get_version_from_config(self._target)
                    if version_from_config:
                        overwritten_version, _ = version_from_config

                # Save the config file, and write our temporary config
                config_used, config_saved = _save_config(Path(self._target))
                if config_used is None:
                    config_used = Path("truffle-config.js")
                _write_config(Path(self._target), config_used, overwritten_version)

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self._target
            )

            stdout_bytes, stderr_bytes = process.communicate()
            stdout, stderr = (
                stdout_bytes.decode(),
                stderr_bytes.decode(),
            )  # convert bytestrings to unicode strings

            if truffle_overwrite_config:
                _reload_config(Path(self._target), config_saved, config_used)

            LOGGER.info(stdout)
            if stderr:
                LOGGER.error(stderr)
        if not os.path.isdir(os.path.join(self._target, build_directory)):
            if os.path.isdir(os.path.join(self._target, "node_modules")):
                raise InvalidCompilation(
                    f"External dependencies {build_directory} {self._target} not found, please install them. (npm install)"
                )
            raise InvalidCompilation("`truffle compile` failed. Can you run it?")
        filenames = glob.glob(os.path.join(self._target, build_directory, "*.json"))

        optimized = None

        version = None
        compiler = None

        for filename_txt in filenames:
            with open(filename_txt, encoding="utf8") as file_desc:
                target_loaded = json.load(file_desc)
                # pylint: disable=too-many-nested-blocks
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
                try:
                    filename = convert_filename(
                        filename, _relative_to_short, crytic_compile, working_dir=self._target
                    )
                except InvalidCompilation as i:
                    txt = str(i)
                    txt += "\nConsider removing the build/contracts content (rm build/contracts/*)"
                    # pylint: disable=raise-missing-from
                    raise InvalidCompilation(txt)

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

        # Avoid conflicts with hardhat
        if os.path.isfile(os.path.join(target, "hardhat.config.js")) | os.path.isfile(
            os.path.join(target, "hardhat.config.ts")
        ):
            return False

        return os.path.isfile(os.path.join(target, "truffle.js")) or os.path.isfile(
            os.path.join(target, "truffle-config.js")
        )

    # pylint: disable=no-self-use
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

    # pylint: disable=no-self-use
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


def _get_version(truffle_call: List[str], cwd: str) -> Tuple[str, str]:
    cmd = truffle_call + ["version"]
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    except OSError as error:
        # pylint: disable=raise-missing-from
        raise InvalidCompilation(f"Truffle failed: {error}")
    stdout, _ = process.communicate()
    stdout = stdout.decode()  # convert bytestrings to unicode strings
    if not stdout:
        raise InvalidCompilation("Truffle failed to run: 'truffle version'")
    stdout = stdout.split("\n")
    for line in stdout:
        if "Solidity" in line:
            if "native" in line:
                return solc.get_version("solc", None), "solc-native"
            version = re.findall(r"\d+\.\d+\.\d+", line)[0]
            compiler = re.findall(r"(solc[a-z\-]*)", line)
            if len(compiler) > 0:
                return version, compiler[0]

    raise InvalidCompilation(f"Solidity version not found {stdout}")


def _save_config(cwd: Path) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Save truffle-config.js / truffle.js to a temporary file.
    Return (original_config_name, temporary_file)
    Return None, None if there was no configuration file

    :param cwd:
    :return:
    """
    unique_filename = str(uuid.uuid4())
    while Path(cwd, unique_filename).exists():
        unique_filename = str(uuid.uuid4())

    if Path(cwd, "truffle-config.js").exists():
        shutil.move(Path(cwd, "truffle-config.js"), Path(cwd, unique_filename))
        return Path("truffle-config.js"), Path(unique_filename)

    if Path(cwd, "truffle.js").exists():
        shutil.move(Path(cwd, "truffle.js"), Path(cwd, unique_filename))
        return Path("truffle.js"), Path(unique_filename)
    return None, None


def _reload_config(cwd: Path, original_config: Optional[Path], tmp_config: Path):
    """
    Restore the original config

    :param cwd:
    :param original_config:
    :param tmp_config:
    :return:
    """
    os.remove(Path(cwd, tmp_config))
    if original_config is not None:
        shutil.move(Path(cwd, original_config), Path(cwd, tmp_config))


def _write_config(cwd: Path, original_config: Path, version: Optional[str]):
    """
    Write the config file

    :param cwd:
    :param original_config:
    :param version:
    :return:
    """
    txt = ""
    if version:
        txt = f"""
    module.exports = {{
      compilers: {{
        solc: {{
          version: "{version}"
        }}
      }}
    }}
    """
    with open(Path(cwd, original_config), "w") as f:
        f.write(txt)


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
