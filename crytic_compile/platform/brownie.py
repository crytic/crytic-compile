import os
import logging
import subprocess
import glob
import json
from pathlib import Path
from .types import Type
from .exceptions import InvalidCompilation
from ..utils.naming import convert_filename
from ..compiler.compiler import CompilerVersion

logger = logging.getLogger("CryticCompile")


def compile(crytic_compile, target, **kwargs):
    build_directory = Path("build", "contracts")
    brownie_ignore_compile = kwargs.get("brownie_ignore_compile", False)
    crytic_compile.type = Type.TRUFFLE

    base_cmd = ["brownie"]

    if not brownie_ignore_compile:
        cmd = base_cmd + ["compile"]

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=target
        )

        stdout, stderr = process.communicate()
        stdout, stderr = (
            stdout.decode(),
            stderr.decode(),
        )  # convert bytestrings to unicode strings

        logger.info(stdout)
        if stderr:
            logger.error(stderr)

    if not os.path.isdir(os.path.join(target, build_directory)):
        raise InvalidCompilation("`brownie compile` failed. Can you run it?")

    filenames = glob.glob(os.path.join(target, build_directory, "*.json"))

    optimized = None
    compiler = "solc"
    version = None

    for filename in filenames:
        with open(filename, encoding="utf8") as f:
            target_loaded = json.load(f)

            if not "ast" in target_loaded:
                continue

            if optimized is None:
                if compiler in target_loaded:
                    compiler = target_loaded["compiler"]
                    optimized = compiler.get("optimize", False)
                    version = _get_version(compiler)

            filename = target_loaded["ast"]["absolutePath"]
            filename = convert_filename(
                filename, _relative_to_short, crytic_compile, working_dir=target
            )

            crytic_compile.asts[filename.absolute] = target_loaded["ast"]
            crytic_compile.filenames.add(filename)
            contract_name = target_loaded["contractName"]
            crytic_compile.contracts_filenames[contract_name] = filename
            crytic_compile.contracts_names.add(contract_name)
            crytic_compile.abis[contract_name] = target_loaded["abi"]
            crytic_compile.bytecodes_init[contract_name] = target_loaded[
                "bytecode"
            ].replace("0x", "")
            crytic_compile.bytecodes_runtime[contract_name] = target_loaded[
                "deployedBytecode"
            ].replace("0x", "")
            crytic_compile.srcmaps_init[contract_name] = target_loaded[
                "sourceMap"
            ].split(";")
            crytic_compile.srcmaps_runtime[contract_name] = target_loaded[
                "deployedSourceMap"
            ].split(";")

    crytic_compile.compiler_version = CompilerVersion(
        compiler=compiler, version=version, optimized=optimized
    )


def is_brownie(target):
    # < 1.1.0: brownie-config.json
    # >= 1.1.0: brownie-config.yaml
    return (os.path.isfile(os.path.join(target, "brownie-config.json")) or
            os.path.isfile(os.path.join(target, "brownie-config.yaml")))


def is_dependency(path):
    return False


def _get_version(compiler):
    version = compiler.get("version", "")
    version = version[len("Version: ") :]
    version = version[0 : version.find("+")]
    print(version)
    return version


def _relative_to_short(relative):
    return relative
