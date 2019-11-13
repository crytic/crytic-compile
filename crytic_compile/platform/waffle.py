import os
import tempfile
import logging
import subprocess
import re
import json
from pathlib import Path
from .types import Type
from .exceptions import InvalidCompilation
from ..utils.naming import convert_filename
from ..compiler.compiler import CompilerVersion

logger = logging.getLogger("CryticCompile")


def compile(crytic_compile, target, **kwargs):

    waffle_ignore_compile = kwargs.get("waffle_ignore_compile", False)
    crytic_compile.type = Type.WAFFLE

    cmd = ["waffle"]
    if not kwargs.get("npx_disable", False):
        cmd = ["npx"] + cmd

    # Default behaviour (without any config_file)
    build_directory = os.path.join("build")
    compiler = "native"
    version = _get_version(compiler, target)
    config = {}

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
        curr_config = config["compilerOptions"]
        curr_needed_config = needed_config["compilerOptions"]
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as f:
            json.dump(config, f)
            f.flush()

            cmd += [os.path.relpath(f.name)]

            logger.info("Temporary file created: {}".format(f.name))
            logger.info("'{}' running".format(" ".join(cmd)))

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=target
            )

            stdout, stderr = process.communicate()
            stdout, stderr = (
                stdout.decode(),
                stderr.decode(),
            )  # convert bytestrings to unicode strings

            if stdout:
                logger.info(stdout)
            if stderr:
                logger.error(stderr)

    if not os.path.isdir(os.path.join(target, build_directory)):
        raise InvalidCompilation(
            "`waffle` compilation failed: build directory not found"
        )

    combined_path = os.path.join(target, build_directory, "Combined-Json.json")
    if not os.path.exists(combined_path):
        raise InvalidCompilation("`Combined-Json.json` not found")

    with open(combined_path, "r") as f:
        target_all = json.load(f)

    optimized = None

    for contract in target_all["contracts"]:
        target_loaded = target_all["contracts"][contract]
        contract = contract.split(":")
        filename_rel = os.path.join(target, contract[0])
        filename = convert_filename(
            filename_rel, _relative_to_short, crytic_compile, working_dir=target
        )

        contract_name = contract[1]

        crytic_compile.asts[filename.absolute] = target_all["sources"][contract[0]][
            "AST"
        ]
        crytic_compile.filenames.add(filename)
        crytic_compile.contracts_filenames[contract_name] = filename
        crytic_compile.contracts_names.add(contract_name)
        crytic_compile.abis[contract_name] = target_loaded["abi"]

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


def is_waffle(target):
    if os.path.isfile(os.path.join(target, "package.json")):
        with open("package.json", encoding="utf8") as f:
            package = json.load(f)
        if "dependencies" in package:
            return "ethereum-waffle" in package["dependencies"]
    return False


def is_dependency(path):
    return "node_modules" in Path(path).parts


def _load_config(config_file):
    with open(config_file, "r") as f:
        content = f.read()

    if "module.exports" in content:
        raise NotImplemented
    else:
        return json.loads(content)


def _get_version(compiler, cwd, config=None):
    if config is not None and "solcVersion" in config:
        version = re.findall("\d+\.\d+\.\d+", config["solcVersion"])[0]

    elif compiler == "dockerized-solc":
        version = config["docker-tag"]

    elif compiler == "native":
        cmd = ["solc", "--version"]
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
        )
        stdout, _ = process.communicate()
        stdout = stdout.decode()  # convert bytestrings to unicode strings
        stdout = stdout.split("\n")
        for line in stdout:
            if "Version" in line:
                version = re.findall("\d+\.\d+\.\d+", line)[0]

    elif compiler == "solc-js":
        cmd = ["solcjs", "--version"]
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
        )
        stdout, _ = process.communicate()
        stdout = stdout.decode()  # convert bytestrings to unicode strings
        version = re.findall("\d+\.\d+\.\d+", stdout)[0]

    else:
        raise InvalidCompilation(f"Solidity version not found {stdout}")

    return version


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
