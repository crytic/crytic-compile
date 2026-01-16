"""
Sourcify platform.

Fetches verified contract source code and compilation artifacts from the Sourcify API.
"""

import json
import logging
import os
import re
import urllib.request
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError, URLError

from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform import solc_standard_json
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.etherscan import _sanitize_remappings
from crytic_compile.platform.exceptions import InvalidCompilation
from crytic_compile.platform.types import Type

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")

SOURCIFY_API_BASE = "https://sourcify.dev/server/v2/contract"


def _get_user_agent() -> str:
    """Get the User-Agent string with package version.

    Returns:
        str: User-Agent string in format "crytic-compile/<version>"
    """
    try:
        pkg_version = version("crytic-compile")
    except Exception:
        pkg_version = "unknown"
    return f"crytic-compile/{pkg_version}"


def _parse_chain_id(chain_id_str: str) -> str:
    """Convert hex or decimal chain ID to decimal string.

    Args:
        chain_id_str: Chain ID as decimal string or hex string (0x prefix)

    Returns:
        str: Chain ID as decimal string
    """
    if chain_id_str.lower().startswith("0x"):
        return str(int(chain_id_str, 16))
    return chain_id_str


def _write_source_files(
    sources: dict[str, dict[str, str]],
    addr: str,
    chain_id: str,
    export_dir: str,
) -> tuple[str, list[str]]:
    """Write source files to disk.

    Args:
        sources: Dict mapping filename to {"content": source_code}
        addr: Contract address
        chain_id: Chain ID
        export_dir: Base export directory

    Returns:
        Tuple of (working_directory, list_of_filenames)

    Raises:
        IOError: If a path would escape the allowed directory
    """
    directory = os.path.join(export_dir, f"sourcify-{chain_id}-{addr}")

    filenames: list[str] = []

    for filename, source_info in sources.items():
        content = source_info.get("content", "")

        path_filename = PurePosixPath(filename)

        # Skip non-Solidity/Vyper files
        if path_filename.suffix not in (".sol", ".vy"):
            continue

        # Handle absolute paths by making them relative
        if path_filename.is_absolute():
            path_filename = PurePosixPath(*path_filename.parts[1:])

        filenames.append(path_filename.as_posix())
        path_filename_disk = Path(directory, path_filename)

        # Security check: ensure path stays within allowed directory
        allowed_path = os.path.abspath(directory)
        if os.path.commonpath((allowed_path, os.path.abspath(path_filename_disk))) != allowed_path:
            raise OSError(
                f"Path '{path_filename_disk}' is outside of the allowed directory: {allowed_path}"
            )

        if not os.path.exists(path_filename_disk.parent):
            os.makedirs(path_filename_disk.parent)

        with open(path_filename_disk, "w", encoding="utf8") as file_desc:
            file_desc.write(content)

    return directory, filenames


def _fetch_sourcify_data(chain_id: str, addr: str) -> dict[str, Any]:
    """Fetch contract data from Sourcify API.

    Args:
        chain_id: Chain ID (decimal string)
        addr: Contract address

    Returns:
        Dict containing sources and compilation data

    Raises:
        InvalidCompilation: If the contract is not found or API request fails
    """
    fields = ",".join(
        [
            "sources",
            "compilation.compilerVersion",
            "compilation.compilerSettings",
            "compilation.name",
        ]
    )
    url = f"{SOURCIFY_API_BASE}/{chain_id}/{addr}?fields={fields}"

    LOGGER.info("Fetching contract from Sourcify: chain=%s address=%s", chain_id, addr)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": _get_user_agent()})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            raise InvalidCompilation(
                f"Contract not verified on Sourcify: chain={chain_id} address={addr}"
            ) from e
        raise InvalidCompilation(f"Sourcify API error: {e}") from e
    except URLError as e:
        raise InvalidCompilation(f"Failed to fetch from Sourcify: {e}") from e

    # Log match type
    match_type = data.get("match", "unknown")
    match_messages = {
        "exact_match": "exact match found",
        "match": "partial match found (metadata may differ)",
    }
    if match_type in match_messages:
        LOGGER.info("Sourcify: %s", match_messages[match_type])
    else:
        LOGGER.warning("Sourcify: unexpected match type: %s", match_type)

    return data


def _write_config_file(working_dir: str, compiler_version: str, settings: dict[str, Any]) -> None:
    """Write crytic_compile.config.json file.

    Args:
        working_dir: Directory to write config to
        compiler_version: Solc version string
        settings: Compiler settings from Sourcify
    """
    optimizer = settings.get("optimizer", {})
    optimization_used = optimizer.get("enabled", False)
    optimize_runs = optimizer.get("runs") if optimization_used else None
    evm_version = settings.get("evmVersion")
    via_ir = settings.get("viaIR")
    remappings = settings.get("remappings", [])

    solc_args: list[str] = []
    if via_ir:
        solc_args.append("--via-ir")
    if optimization_used:
        solc_args.append(f"--optimize --optimize-runs {optimize_runs}")
    if evm_version:
        solc_args.append(f"--evm-version {evm_version}")

    metadata_config: dict[str, Any] = {
        "solc_remaps": _sanitize_remappings(remappings, working_dir) if remappings else {},
        "solc_solcs_select": compiler_version,
        "solc_args": " ".join(solc_args),
    }

    config_path = os.path.join(working_dir, "crytic_compile.config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(metadata_config, f)


class Sourcify(AbstractPlatform):
    """
    Sourcify platform - fetches verified contracts from sourcify.dev
    """

    NAME = "Sourcify"
    PROJECT_URL = "https://sourcify.dev/"
    TYPE = Type.SOURCIFY

    def compile(self, crytic_compile: "CryticCompile", **kwargs: str) -> None:
        """Run the compilation by fetching from Sourcify.

        Args:
            crytic_compile: Associated CryticCompile object
            **kwargs: Optional arguments. Used: "export_dir", "solc"

        Raises:
            InvalidCompilation: If the contract is not found or API request fails
        """
        # Parse target: sourcify-<chainId>:0x<address>
        match = re.match(r"^sourcify-(0x[a-fA-F0-9]+|\d+):(0x[a-fA-F0-9]{40})$", self._target)
        if not match:
            raise InvalidCompilation(f"Invalid Sourcify target format: {self._target}")

        chain_id = _parse_chain_id(match.group(1))
        addr = match.group(2)

        # Prepare export directory
        export_dir = os.path.join(kwargs.get("export_dir", "crytic-export"), "sourcify-contracts")
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        # Fetch from Sourcify API
        data = _fetch_sourcify_data(chain_id, addr)

        sources = data.get("sources", {})
        if not sources:
            raise InvalidCompilation("No source files returned from Sourcify")

        working_dir, filenames = _write_source_files(sources, addr, chain_id, export_dir)

        # Extract compilation settings
        compilation = data.get("compilation", {})
        compiler_version_str = compilation.get("compilerVersion", "")
        version_match = re.search(r"(\d+\.\d+\.\d+)", compiler_version_str)
        if not version_match:
            raise InvalidCompilation(
                f"Could not parse compiler version from: {compiler_version_str}"
            )
        compiler_version = version_match.group(1)

        settings = compilation.get("compilerSettings", {})
        optimizer = settings.get("optimizer", {})
        optimization_used = optimizer.get("enabled", False)
        remappings = _sanitize_remappings(settings.get("remappings", []), working_dir) or None

        # Create and configure compilation unit
        compilation_unit = CompilationUnit(crytic_compile, compilation.get("name", "Contract"))
        compilation_unit.compiler_version = CompilerVersion(
            compiler=kwargs.get("solc", "solc"),
            version=compiler_version,
            optimized=optimization_used,
            optimize_runs=optimizer.get("runs") if optimization_used else None,
        )
        compilation_unit.compiler_version.look_for_installed_version()

        solc_standard_json.standalone_compile(
            filenames,
            compilation_unit,
            working_dir=working_dir,
            remappings=remappings,
            evm_version=settings.get("evmVersion"),
            via_ir=settings.get("viaIR"),
        )

        _write_config_file(working_dir, compiler_version, settings)

    def clean(self, **_kwargs: str) -> None:
        # No-op for Sourcify (remote platform)
        pass

    @staticmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """Check if the target is a Sourcify target.

        Args:
            target: Path to the target
            **kwargs: Optional arguments (unused)

        Returns:
            bool: True if the target is a Sourcify target
        """
        # Match sourcify-<chainId>:0x<address> where chainId is decimal or 0x hex
        return bool(re.match(r"^sourcify-(0x[a-fA-F0-9]+|\d+):0x[a-fA-F0-9]{40}$", target))

    def is_dependency(self, path: str) -> bool:
        """Check if the path is a dependency.

        Args:
            path: Path to the target

        Returns:
            bool: Always False for Sourcify
        """
        return False

    def _guessed_tests(self) -> list[str]:
        """Guess the potential unit tests commands.

        Returns:
            List[str]: Empty list (no tests for remote contracts)
        """
        return []
