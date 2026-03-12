"""
Etherscan platform.
"""

import json
import logging
import os
import re
import urllib.request
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING

from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform import solc_standard_json
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.explorer_utils import (
    EXPLORER_BASE_BYTECODE,
    convert_version,
    handle_bytecode,
    handle_multiple_files,
    handle_single_file,
)
from crytic_compile.platform.types import Type

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")


# Etherscan v1 API style (per-scanner URL)
ETHERSCAN_BASE_V1 = "https://api%s/api?module=contract&action=getsourcecode&address=%s"

# Etherscan v2 API style (unified)
ETHERSCAN_BASE_V2 = (
    "https://api.etherscan.io/v2/api?chainid=%s&module=contract&action=getsourcecode&address=%s"
)

# v1 style scanners
SUPPORTED_NETWORK_V1: dict[str, tuple[str, str]] = {
    # None at this time. External tracer instances not operated by Etherscan would be here
}

# v2 style scanners
SUPPORTED_NETWORK_V2: dict[str, tuple[str, str]] = {
    # Key, (chainid, perfix_bytecode)
    "mainnet": ("1", "etherscan.io"),
    "sepolia": ("11155111", "sepolia.etherscan.io"),
    "holesky": ("17000", "holesky.etherscan.io"),
    "hoodi": ("560048", "hoodi.etherscan.io"),
    "bsc": ("56", "bscscan.com"),
    "testnet.bsc": ("97", "testnet.bscscan.com"),
    "poly": ("137", "polygonscan.com"),
    "amoy.poly": ("80002", "amoy.polygonscan.com"),
    "base": ("8453", "basescan.org"),
    "sepolia.base": ("84532", "sepolia.basescan.org"),
    "arbi": ("42161", "arbiscan.io"),
    "nova.arbi": ("42170", "nova.arbiscan.io"),
    "sepolia.arbi": ("421614", "sepolia.arbiscan.io"),
    "linea": ("59144", "lineascan.build"),
    "sepolia.linea": ("59141", "sepolia.lineascan.build"),
    "blast": ("81457", "blastscan.io"),
    "sepolia.blast": ("168587773", "sepolia.blastscan.io"),
    "optim": ("10", "optimistic.etherscan.io"),
    "sepolia.optim": ("11155420", "sepolia-optimism.etherscan.io"),
    "avax": ("43114", "snowscan.xyz"),
    "testnet.avax": ("43113", "testnet.snowscan.xyz"),
    "bttc": ("199", "bttcscan.com"),
    "testnet.bttc": ("1029", "testnet.bttcscan.com"),
    "celo": ("42220", "celoscan.io"),
    "sepolia.celo": ("11142220", "sepolia.celoscan.io"),
    "frax": ("252", "fraxscan.com"),
    "hoodi.frax": ("2523", "hoodi.fraxscan.com"),
    "gno": ("100", "gnosisscan.io"),
    "mantle": ("5000", "mantlescan.xyz"),
    "sepolia.mantle": ("5003", "sepolia.mantlescan.xyz"),
    "memecore": ("43521", "testnet.memecorescan.io"),
    "moonbeam": ("1284", "moonbeam.moonscan.io"),
    "moonriver": ("1285", "moonriver.moonscan.io"),
    "moonbase": ("1287", "moonbase.moonscan.io"),
    "opbnb": ("204", "opbnb.bscscan.com"),
    "testnet.opbnb": ("5611", "opbnb-testnet.bscscan.com"),
    "scroll": ("534352", "scrollscan.com"),
    "sepolia.scroll": ("534351", "sepolia.scrollscan.com"),
    "taiko": ("167000", "taikoscan.io"),
    "hoodi.taiko": ("167013", "hoodi.taikoscan.io"),
    "era.zksync": ("324", "era.zksync.network"),
    "sepoliaera.zksync": ("300", "sepolia-era.zksync.network"),
    "xdc": ("50", "xdcscan.com"),
    "testnet.xdc": ("51", "testnet.xdcscan.com"),
    "apechain": ("33139", "apescan.io"),
    "curtis.apechain": ("33111", "curtis.apescan.io"),
    "world": ("480", "worldscan.org"),
    "sepolia.world": ("4801", "sepolia.worldscan.org"),
    "sophon": ("50104", "sophscan.xyz"),
    "testnet.sophon": ("531050104", "testnet.sophscan.xyz"),
    "sonic": ("146", "sonicscan.org"),
    "testnet.sonic": ("14601", "testnet.sonicscan.org"),
    "unichain": ("130", "uniscan.xyz"),
    "sepolia.unichain": ("1301", "sepolia.uniscan.xyz"),
    "abstract": ("2741", "abscan.org"),
    "sepolia.abstract": ("11124", "sepolia.abscan.org"),
    "berachain": ("80094", "berascan.com"),
    "testnet.berachain": ("80069", "testnet.berascan.com"),
    "swellchain": ("1923", "swellchainscan.io"),
    "testnet.swellchain": ("1924", "sepolia.swellchainscan.io"),
    "monad": ("143", "monadscan.com"),
    "testnet.monad": ("10143", "testnet.monadscan.com"),
    "hyperevm": ("999", "hyperevmscan.io"),
    "katana": ("747474", "katanascan.com"),
    "bokuto.katana": ("737373", "bokuto.katanascan.com"),
    "sei": ("1329", "seiscan.io"),
    "testnet.sei": ("1328", "testnet.seiscan.io"),
}

SUPPORTED_NETWORK = {**SUPPORTED_NETWORK_V1, **SUPPORTED_NETWORK_V2}


def generate_supported_network_v2_list() -> None:
    """Manual function to generate a dictionary for updating the SUPPORTED_NETWORK_V2 array"""

    with urllib.request.urlopen("https://api.etherscan.io/v2/chainlist") as response:
        items = response.read()
    networks = json.loads(items)

    id2name = {}
    for name, (chainid, _) in SUPPORTED_NETWORK_V2.items():
        id2name[chainid] = name

    results = {}
    for network in networks["result"]:
        name = id2name.get(network["chainid"], f"{network['chainid']}")
        results[name] = (
            network["chainid"],
            network["blockexplorer"].replace("https://", "").strip("/"),
        )

    print(results)


class Etherscan(AbstractPlatform):
    """
    Etherscan platform
    """

    NAME = "Etherscan"
    PROJECT_URL = "https://etherscan.io/"
    TYPE = Type.ETHERSCAN

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str) -> None:
        """Run the compilation

        Args:
            crytic_compile (CryticCompile): Associated CryticCompile object
            **kwargs: optional arguments. Used "solc", "explorer_only_source_code", "explorer_only_bytecode",
                "etherscan_api_key", "export_dir"

        Raises:
            InvalidCompilation: if etherscan returned an error, or its results were not correctly parsed
        """

        target = self._target

        api_key_required = None

        if target.startswith(tuple(SUPPORTED_NETWORK_V2)):
            api_key_required = 2
            prefix, addr = target.split(":", 2)
            chainid, prefix_bytecode = SUPPORTED_NETWORK_V2[prefix]
            etherscan_url = ETHERSCAN_BASE_V2 % (chainid, addr)
            etherscan_bytecode_url = EXPLORER_BASE_BYTECODE % (prefix_bytecode, addr)
        elif target.startswith(tuple(SUPPORTED_NETWORK_V1)):
            api_key_required = 1
            prefix = SUPPORTED_NETWORK_V1[target[: target.find(":") + 1]][0]
            prefix_bytecode = SUPPORTED_NETWORK_V1[target[: target.find(":") + 1]][1]
            addr = target[target.find(":") + 1 :]
            etherscan_url = ETHERSCAN_BASE_V1 % (prefix, addr)
            etherscan_bytecode_url = EXPLORER_BASE_BYTECODE % (prefix_bytecode, addr)
        else:
            api_key_required = 2
            etherscan_url = ETHERSCAN_BASE_V2 % ("1", target)
            etherscan_bytecode_url = EXPLORER_BASE_BYTECODE % ("etherscan.io", target)
            addr = target
            prefix = None

        only_source = kwargs.get("explorer_only_source_code", False)
        only_bytecode = kwargs.get("explorer_only_bytecode", False)

        etherscan_api_key = kwargs.get("etherscan_api_key", None)
        if etherscan_api_key is None:
            etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")

        export_dir = kwargs.get("export_dir", "crytic-export")
        export_dir = os.path.join(
            export_dir, kwargs.get("explorer_export_dir") or "etherscan-contracts"
        )

        if api_key_required == 2 and etherscan_api_key:
            etherscan_url += f"&apikey={etherscan_api_key}"
            etherscan_bytecode_url += f"&apikey={etherscan_api_key}"
        # API key handling for external tracers would be here e.g.
        # elif api_key_required == 1 and avax_api_key and "snowtrace" in etherscan_url:
        #    etherscan_url += f"&apikey={avax_api_key}"
        #    etherscan_bytecode_url += f"&apikey={avax_api_key}"

        source_code: str = ""
        result: dict[str, bool | str | int] = {}
        contract_name: str = ""

        if not only_bytecode:
            # build object with headers, then send request
            new_etherscan_url = urllib.request.Request(
                etherscan_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36 crytic-compile/0"
                },
            )
            with urllib.request.urlopen(new_etherscan_url) as response:
                html = response.read()

            info = json.loads(html)

            if (
                "result" in info
                and "rate limit reached" in info["result"]
                and "message" in info
                and info["message"] == "NOTOK"
            ):
                LOGGER.error("Etherscan API rate limit exceeded")
                raise InvalidCompilation("Etherscan API rate limit exceeded")

            if "message" not in info:
                LOGGER.error("Incorrect etherscan request")
                raise InvalidCompilation("Incorrect etherscan request " + etherscan_url)

            if not info["message"].startswith("OK") and "Invalid API Key" in info["result"]:
                LOGGER.error("Invalid etherscan API Key")
                raise InvalidCompilation("Invalid etherscan API Key: " + etherscan_url)

            if not info["message"].startswith("OK"):
                LOGGER.error("Contract has no public source code")
                raise InvalidCompilation("Contract has no public source code: " + etherscan_url)

            if "result" not in info:
                LOGGER.error("Contract has no public source code")
                raise InvalidCompilation("Contract has no public source code: " + etherscan_url)

            result = info["result"][0]

            if "ABI" in result and "Contract source code not verified" in result["ABI"]:
                LOGGER.error("Contract has no public source code")
                raise InvalidCompilation("Contract has no public source code: " + etherscan_url)

            # Assert to help mypy
            assert isinstance(result["SourceCode"], str)
            assert isinstance(result["ContractName"], str)
            source_code = result["SourceCode"]
            contract_name = result["ContractName"]

        if source_code == "" and not only_source:
            LOGGER.info("Source code not available, try to fetch the bytecode only")

            req = urllib.request.Request(
                etherscan_bytecode_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req) as response:
                html = response.read()

            handle_bytecode(crytic_compile, target, html)
            return

        if source_code == "":
            LOGGER.error("Contract has no public source code")
            raise InvalidCompilation("Contract has no public source code: " + etherscan_url)

        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        # Assert to help mypy
        assert isinstance(result["CompilerVersion"], str)

        compiler_version = re.findall(r"\d+\.\d+\.\d+", convert_version(result["CompilerVersion"]))[
            0
        ]

        # etherscan can report "default" which is not a valid EVM version
        evm_version: str | None = None
        if "EVMVersion" in result:
            assert isinstance(result["EVMVersion"], str)
            evm_version = result["EVMVersion"] if result["EVMVersion"] != "Default" else None

        optimization_used: bool = result["OptimizationUsed"] == "1"

        optimize_runs = None
        if optimization_used:
            optimize_runs = int(result["Runs"])

        working_dir: str | None = None
        remappings: list[str] | None = None

        dict_source_code: dict | None = None
        try:
            # etherscan might return an object with two curly braces, {{ content }}
            dict_source_code = json.loads(source_code[1:-1])
            assert isinstance(dict_source_code, dict)
            filenames, working_dir, remappings = handle_multiple_files(
                dict_source_code, addr, prefix, contract_name, export_dir
            )
        except JSONDecodeError:
            try:
                # or etherscan might return an object with single curly braces, { content }
                dict_source_code = json.loads(source_code)
                assert isinstance(dict_source_code, dict)
                filenames, working_dir, remappings = handle_multiple_files(
                    dict_source_code, addr, prefix, contract_name, export_dir
                )
            except JSONDecodeError:
                filenames = [
                    handle_single_file(source_code, addr, prefix, contract_name, export_dir)
                ]

        # viaIR is not exposed on the top level JSON offered by etherscan, so we need to inspect the settings
        via_ir_enabled: bool | None = None
        if isinstance(dict_source_code, dict):
            via_ir_enabled = dict_source_code.get("settings", {}).get("viaIR", None)

        compilation_unit = CompilationUnit(crytic_compile, contract_name)

        compilation_unit.compiler_version = CompilerVersion(
            compiler=kwargs.get("solc", "solc"),
            version=compiler_version,
            optimized=optimization_used,
            optimize_runs=optimize_runs,
        )
        compilation_unit.compiler_version.look_for_installed_version()

        if "Proxy" in result and result["Proxy"] == "1":
            assert "Implementation" in result
            implementation = str(result["Implementation"])
            if target.startswith(tuple(SUPPORTED_NETWORK)):
                implementation = f"{target[: target.find(':')]}:{implementation}"
            compilation_unit.implementation_addresses.add(implementation)

        solc_standard_json.standalone_compile(
            filenames,
            compilation_unit,
            working_dir=working_dir,
            remappings=remappings,
            evm_version=evm_version,
            via_ir=via_ir_enabled,
        )

        metadata_config = {
            "solc_remaps": remappings if remappings else {},
            "solc_solcs_select": compiler_version,
            "solc_args": " ".join(
                filter(
                    None,
                    [
                        "--via-ir" if via_ir_enabled else "",
                        "--optimize --optimize-runs " + str(optimize_runs) if optimize_runs else "",
                        "--evm-version " + evm_version if evm_version else "",
                    ],
                )
            ),
        }

        with open(
            os.path.join(working_dir if working_dir else export_dir, "crytic_compile.config.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(metadata_config, f)

    def clean(self, **_kwargs: str) -> None:
        pass

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """Check if the target is a etherscan project

        Args:
            target (str): path to the target
            **kwargs: optional arguments. Used "explorer_ignore"

        Returns:
            bool: True if the target is a etherscan project
        """
        if kwargs.get("explorer_ignore", False):
            return False
        if target.startswith(tuple(SUPPORTED_NETWORK)):
            target = target[target.find(":") + 1 :]
        return bool(re.match(r"^\s*0x[a-zA-Z0-9]{40}\s*$", target))

    def is_dependency(self, path: str) -> bool:
        """Check if the path is a dependency

        Args:
            path (str): path to the target

        Returns:
            bool: True if the target is a dependency
        """
        return False

    def _guessed_tests(self) -> list[str]:
        """Guess the potential unit tests commands

        Returns:
            List[str]: The guessed unit tests commands
        """
        return []
