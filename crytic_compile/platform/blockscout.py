"""
Blockscout platform — fetches verified contracts from Blockscout-based explorers.
"""

import json
import logging
import os
import re
import urllib.request
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any

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

# Blockscout API endpoint — host is the full hostname (no api. subdomain)
BLOCKSCOUT_BASE = "https://%s/api?module=contract&action=getsourcecode&address=%s"

# Key -> (api_host, bytecode_host)
SUPPORTED_NETWORK_BLOCKSCOUT: dict[str, tuple[str, str]] = {
    "flow": ("evm.flowscan.io", "evm.flowscan.io"),
    "ink": ("explorer.inkonchain.com", "explorer.inkonchain.com"),
    "metis": ("andromeda-explorer.metis.io", "andromeda-explorer.metis.io"),
    "plume": ("explorer.plume.org", "explorer.plume.org"),
    "story": ("www.storyscan.xyz", "www.storyscan.xyz"),
}


def _normalize_blockscout_result(result: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Blockscout API result to Etherscan field conventions.

    Blockscout differs from Etherscan in field names and value formats.
    This converts them so the compilation pipeline can work unchanged.

    Args:
        result: Raw result dict from a Blockscout getsourcecode response.

    Returns:
        dict: Normalized result with Etherscan-compatible field names and values.
    """
    normalized = dict(result)

    # OptimizationUsed: "true"/"false" -> "1"/"0"
    if "OptimizationUsed" in normalized:
        normalized["OptimizationUsed"] = "1" if normalized["OptimizationUsed"] == "true" else "0"

    # OptimizationRuns (int) -> Runs (str)
    if "OptimizationRuns" in normalized and "Runs" not in normalized:
        normalized["Runs"] = str(normalized["OptimizationRuns"])

    # IsProxy -> Proxy ("1"/"0") + Implementation
    if "IsProxy" in normalized:
        normalized["Proxy"] = "1" if normalized["IsProxy"] == "true" else "0"
        if normalized["Proxy"] == "1":
            normalized["Implementation"] = normalized.get("ImplementationAddress", "")

    # Reconstruct SourceCode as a multi-file JSON blob from FileName + AdditionalSources.
    # Blockscout stores the main file in SourceCode with extras in AdditionalSources,
    # while Etherscan encodes everything as {"sources": {filename: {content: ...}}} in SourceCode.
    additional = normalized.get("AdditionalSources", [])
    main_filename = normalized.get("FileName", "")
    if additional or main_filename:
        sources: dict[str, dict[str, str]] = {}
        if main_filename and normalized.get("SourceCode"):
            sources[main_filename] = {"content": normalized["SourceCode"]}
        for src in additional:
            # Blockscout uses "Filename" (lowercase n) in AdditionalSources entries
            src_filename = src.get("Filename") or src.get("FileName", "")
            src_code = src.get("SourceCode", "")
            if src_filename and src_code:
                sources[src_filename] = {"content": src_code}
        settings = normalized.get("CompilerSettings", {})
        payload: dict[str, Any] = {"sources": sources}
        if settings:
            payload["settings"] = settings
        normalized["SourceCode"] = json.dumps(payload)

    return normalized


class Blockscout(AbstractPlatform):
    """
    Blockscout platform — fetches verified contracts from Blockscout-based explorers.
    """

    NAME = "Blockscout"
    PROJECT_URL = "https://www.blockscout.com/"
    TYPE = Type.BLOCKSCOUT

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str) -> None:
        """Run the compilation.

        Args:
            crytic_compile: Associated CryticCompile object.
            **kwargs: optional arguments. Used "solc", "etherscan_only_source_code",
                "etherscan_only_bytecode", "export_dir".

        Raises:
            InvalidCompilation: if the explorer returned an error or results could not be parsed.
        """
        target = self._target
        prefix, addr = target.split(":", 1)
        api_host, bytecode_host = SUPPORTED_NETWORK_BLOCKSCOUT[prefix]

        source_url = BLOCKSCOUT_BASE % (api_host, addr)
        bytecode_url = EXPLORER_BASE_BYTECODE % (bytecode_host, addr)

        only_source = kwargs.get("etherscan_only_source_code", False)
        only_bytecode = kwargs.get("etherscan_only_bytecode", False)

        export_dir = kwargs.get("export_dir", "crytic-export")
        export_dir = os.path.join(
            export_dir, kwargs.get("etherscan_export_dir", "etherscan-contracts")
        )

        source_code: str = ""
        result: dict[str, Any] = {}
        contract_name: str = ""

        if not only_bytecode:
            req = urllib.request.Request(
                source_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36 crytic-compile/0"
                },
            )
            with urllib.request.urlopen(req) as response:
                html = response.read()

            info = json.loads(html)

            if "message" not in info:
                LOGGER.error("Incorrect Blockscout request")
                raise InvalidCompilation("Incorrect Blockscout request " + source_url)

            if not info["message"].startswith("OK"):
                LOGGER.error("Contract has no public source code")
                raise InvalidCompilation("Contract has no public source code: " + source_url)

            if "result" not in info:
                LOGGER.error("Contract has no public source code")
                raise InvalidCompilation("Contract has no public source code: " + source_url)

            result = _normalize_blockscout_result(info["result"][0])

            if "ABI" in result and "Contract source code not verified" in str(result["ABI"]):
                LOGGER.error("Contract has no public source code")
                raise InvalidCompilation("Contract has no public source code: " + source_url)

            # Assert to help mypy
            assert isinstance(result["SourceCode"], str)
            assert isinstance(result["ContractName"], str)
            source_code = result["SourceCode"]
            contract_name = result["ContractName"]

        if source_code == "" and not only_source:
            LOGGER.info("Source code not available, try to fetch the bytecode only")
            req = urllib.request.Request(bytecode_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response:
                html = response.read()
            handle_bytecode(crytic_compile, target, html)
            return

        if source_code == "":
            LOGGER.error("Contract has no public source code")
            raise InvalidCompilation("Contract has no public source code: " + source_url)

        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        # Assert to help mypy
        assert isinstance(result["CompilerVersion"], str)
        compiler_version = re.findall(r"\d+\.\d+\.\d+", convert_version(result["CompilerVersion"]))[
            0
        ]

        evm_version: str | None = None
        if "EVMVersion" in result:
            assert isinstance(result["EVMVersion"], str)
            evm_version = (
                result["EVMVersion"]
                if result["EVMVersion"].lower() not in ("default", "")
                else None
            )

        optimization_used: bool = result["OptimizationUsed"] == "1"
        optimize_runs = None
        if optimization_used:
            optimize_runs = int(result["Runs"])

        working_dir: str | None = None
        remappings: list[str] | None = None
        dict_source_code: dict | None = None

        try:
            # Etherscan wraps multi-file source in double braces: {{ content }}
            dict_source_code = json.loads(source_code[1:-1])
            assert isinstance(dict_source_code, dict)
            filenames, working_dir, remappings = handle_multiple_files(
                dict_source_code, addr, prefix, contract_name, export_dir
            )
        except JSONDecodeError:
            try:
                # _normalize_blockscout_result produces a single-brace JSON: { content }
                dict_source_code = json.loads(source_code)
                assert isinstance(dict_source_code, dict)
                filenames, working_dir, remappings = handle_multiple_files(
                    dict_source_code, addr, prefix, contract_name, export_dir
                )
            except JSONDecodeError:
                filenames = [
                    handle_single_file(source_code, addr, prefix, contract_name, export_dir)
                ]

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

        if result.get("Proxy") == "1" and result.get("Implementation"):
            implementation = f"{prefix}:{result['Implementation']}"
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
        """Check if the target is a Blockscout-hosted contract.

        Args:
            target: path/target string.
            **kwargs: optional arguments. Used "etherscan_ignore".

        Returns:
            bool: True if the target uses a known Blockscout network prefix.
        """
        # Blockscout respects the same ignore flag as Etherscan so that a single
        # flag suppresses all block explorer platforms.
        if kwargs.get("etherscan_ignore", False):
            return False
        if not target.startswith(tuple(SUPPORTED_NETWORK_BLOCKSCOUT)):
            return False
        addr = target[target.find(":") + 1 :]
        return bool(re.match(r"^\s*0x[a-zA-Z0-9]{40}\s*$", addr))

    def is_dependency(self, path: str) -> bool:
        return False

    def _guessed_tests(self) -> list[str]:
        return []
