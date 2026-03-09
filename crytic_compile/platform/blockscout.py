"""
Blockscout platform — fetches verified contracts from Blockscout-based explorers.
"""

import json
import logging
import os
import re
import urllib.error
import urllib.parse
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
from crytic_compile.platform.sourcify import try_compile_from_sourcify
from crytic_compile.platform.types import Type

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")

# Blockscout API endpoint — explorer_url is the full base URL
BLOCKSCOUT_BASE = "%s/api?module=contract&action=getsourcecode&address=%s"

# Blockscout chain directory API
BLOCKSCOUT_CHAINS_URL = "https://chains.blockscout.com/api/chains"

# Chains with Blockscout-compatible explorers not listed in the directory.
# Checked first so they cannot be shadowed by directory conflicts.
BLOCKSCOUT_EXTRA_CHAINS: dict[str, str] = {
    "747": "https://evm.flowscan.io",  # Flow
    "98866": "https://explorer.plume.org",  # Plume
}

# Module-level cache: chain_id (str) -> explorer_url (str)
_blockscout_chains: dict[str, str] | None = None


def _fetch_blockscout_chains() -> dict[str, str]:
    """Fetch the Blockscout chain directory and return a
    chain_id -> explorer_url mapping.

    Results are cached after the first successful call.

    Returns:
        Mapping of chain ID strings to explorer base URLs.
    """
    global _blockscout_chains  # noqa: PLW0603
    if _blockscout_chains is not None:
        return _blockscout_chains

    try:
        req = urllib.request.Request(
            BLOCKSCOUT_CHAINS_URL,
            headers={"User-Agent": "crytic-compile/0"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        LOGGER.warning("Failed to fetch Blockscout chain list: %s", e)
        _blockscout_chains = {}
        return _blockscout_chains

    chains: dict[str, str] = {}
    for chain_id, info in data.items():
        explorers = info.get("explorers", [])
        if explorers:
            url = explorers[0].get("url", "").rstrip("/")
            if url:
                chains[chain_id] = url

    # Extra chains take priority over the directory (avoids conflicts
    # like chain 747 mapping to Alvey instead of Flow).
    chains.update(BLOCKSCOUT_EXTRA_CHAINS)

    _blockscout_chains = chains
    return _blockscout_chains


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
            **kwargs: optional arguments. Used "solc", "explorer_only_source_code",
                "explorer_only_bytecode", "export_dir".

        Raises:
            InvalidCompilation: if the explorer returned an error or results could not be parsed.
        """
        target = self._target
        match = re.match(r"^blockscout-(\d+):(0x[a-fA-F0-9]{40})$", target)
        if not match:
            raise InvalidCompilation(f"Invalid Blockscout target: {target}")

        chain_id = match.group(1)
        addr = match.group(2)
        prefix = f"blockscout-{chain_id}"

        custom_url = kwargs.get("blockscout_url")
        if custom_url:
            explorer_url = custom_url.rstrip("/")
        else:
            chains = _fetch_blockscout_chains()
            if chain_id not in chains:
                raise InvalidCompilation(
                    f"Chain {chain_id} not found in Blockscout "
                    f"chain list. Use --blockscout-url to "
                    f"specify a custom explorer URL, or see "
                    f"https://chains.blockscout.com/ for "
                    f"supported chains."
                )
            explorer_url = chains[chain_id]
        explorer_host = urllib.parse.urlparse(explorer_url).netloc

        source_url = BLOCKSCOUT_BASE % (explorer_url, addr)
        bytecode_url = EXPLORER_BASE_BYTECODE % (explorer_host, addr)

        only_source = kwargs.get("explorer_only_source_code", False)
        only_bytecode = kwargs.get("explorer_only_bytecode", False)

        export_dir = kwargs.get("export_dir", "crytic-export")
        export_dir = os.path.join(
            export_dir, kwargs.get("explorer_export_dir") or "blockscout-contracts"
        )

        # Try Sourcify first — it carries richer metadata and is preferred when available.
        if not only_bytecode:
            base_export = kwargs.get("export_dir", "crytic-export")
            sourcify_kwargs = {k: v for k, v in kwargs.items() if k != "export_dir"}
            if try_compile_from_sourcify(
                crytic_compile, chain_id, addr, base_export, **sourcify_kwargs
            ):
                LOGGER.info("Compiled %s via Sourcify (chain %s)", addr, chain_id)
                return

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
            **kwargs: optional arguments. Used "explorer_ignore".

        Returns:
            bool: True if the target matches blockscout-<chainid>:0x<address>.
        """
        if kwargs.get("explorer_ignore", False):
            return False
        return bool(re.match(r"^blockscout-\d+:0x[a-fA-F0-9]{40}$", target))

    def is_dependency(self, path: str) -> bool:
        return False

    def _guessed_tests(self) -> list[str]:
        return []
