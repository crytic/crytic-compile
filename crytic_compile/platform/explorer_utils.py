"""Shared utilities for block explorer platforms (Etherscan, Blockscout)."""

import logging
import os
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.utils.naming import Filename

if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")

# Block explorer address page URL — used to scrape bytecode when source is unavailable.
# Both Etherscan and Blockscout use this URL pattern.
EXPLORER_BASE_BYTECODE = "https://%s/address/%s#code"


def convert_version(version: str) -> str:
    """Convert the compiler version string from explorer format to a bare semver.

    Args:
        version (str): original version, e.g. "v0.8.20+commit.a1b79de6"

    Returns:
        str: version without leading "v" or "+commit..." suffix
    """
    if "+" in version:
        return version[1 : version.find("+")]
    return version[1:]


def handle_bytecode(crytic_compile: "CryticCompile", target: str, result_b: bytes) -> None:
    """Parse the bytecode scraped from an explorer page and populate CryticCompile.

    Args:
        crytic_compile (CryticCompile): Associated CryticCompile object.
        target (str): path to the target.
        result_b (bytes): raw HTML containing the bytecode.
    """
    # There is no direct API to get the bytecode from block explorers.
    # The page changes from time to time; this simple parsing is not guaranteed to be robust.
    begin = """Search Algorithm">\nSimilar Contracts</button>\n"""
    begin += """<div id="dividcode">\n<pre class=\'wordwrap\' style=\'height: 15pc;\'>0x"""
    result = result_b.decode("utf8")
    result = result[result.find(begin) + len(begin) :]
    bytecode = result[: result.find("<")]

    contract_name = f"Contract_{target}"
    contract_filename = Filename(absolute="", relative="", short="", used="")

    compilation_unit = CompilationUnit(crytic_compile, str(target))
    source_unit = compilation_unit.create_source_unit(contract_filename)

    source_unit.add_contract_name(contract_name)
    compilation_unit.filename_to_contracts[contract_filename].add(contract_name)
    source_unit.abis[contract_name] = {}
    source_unit.bytecodes_init[contract_name] = bytecode
    source_unit.bytecodes_runtime[contract_name] = ""
    source_unit.srcmaps_init[contract_name] = []
    source_unit.srcmaps_runtime[contract_name] = []

    compilation_unit.compiler_version = CompilerVersion(
        compiler="unknown", version="", optimized=False
    )

    crytic_compile.bytecode_only = True


def handle_single_file(
    source_code: str, addr: str, prefix: str | None, contract_name: str, export_dir: str
) -> str:
    """Write a single-file contract to disk and return the filename.

    Args:
        source_code (str): source code.
        addr (str): contract address.
        prefix (Optional[str]): chain prefix, used to disambiguate filenames.
        contract_name (str): contract name.
        export_dir (str): directory where the file will be written.

    Returns:
        str: path to the written file.
    """
    if prefix:
        filename = os.path.join(export_dir, f"{addr}{prefix}-{contract_name}.sol")
    else:
        filename = os.path.join(export_dir, f"{addr}-{contract_name}.sol")

    with open(filename, "w", encoding="utf8") as file_desc:
        file_desc.write(source_code)

    return filename


def handle_multiple_files(
    dict_source_code: dict, addr: str, prefix: str | None, contract_name: str, export_dir: str
) -> tuple[list[str], str, list[str] | None]:
    """Write a multi-file contract to disk and return the filenames, working dir, and remappings.

    Args:
        dict_source_code (dict): parsed source object from an explorer API response.
        addr (str): contract address.
        prefix (Optional[str]): chain prefix, used to disambiguate directories.
        contract_name (str): contract name.
        export_dir (str): base directory where files will be written.

    Returns:
        Tuple[List[str], str, Optional[List[str]]]: filenames, working directory, remappings.

    Raises:
        OSError: if a source path would escape the working directory.
    """
    if prefix:
        directory = os.path.join(export_dir, f"{addr}{prefix}-{contract_name}")
    else:
        directory = os.path.join(export_dir, f"{addr}-{contract_name}")

    if "sources" in dict_source_code:
        # explorer may return {"sources": {filename: {content: ...}, ...}}
        source_codes = dict_source_code["sources"]
    else:
        # or directly {filename: {content: ...}, ...}
        source_codes = dict_source_code

    filtered_paths: list[str] = []
    for filename, source_code in source_codes.items():
        path_filename = PurePosixPath(filename)
        if path_filename.suffix not in [".sol", ".vy"]:
            continue

        # https://etherscan.io/address/0x19bb64b80cbf61e61965b0e5c2560cc7364c6546#code has an import of erc721a/contracts/ERC721A.sol
        # if the full path is lost then won't compile
        if "contracts" == path_filename.parts[0] and not filename.startswith("@"):
            path_filename = PurePosixPath(
                *path_filename.parts[path_filename.parts.index("contracts") :]
            )

        # Convert "absolute" paths such as "/interfaces/IFoo.sol" into relative ones.
        # This is needed due to the following behavior from pathlib.Path:
        # > When several absolute paths are given, the last is taken as an anchor
        # We need to make sure this is relative, so that Path(directory, ...) remains anchored to directory
        if path_filename.is_absolute():
            path_filename = PurePosixPath(*path_filename.parts[1:])

        filtered_paths.append(path_filename.as_posix())
        path_filename_disk = Path(directory, path_filename)

        allowed_path = os.path.abspath(directory)
        if os.path.commonpath((allowed_path, os.path.abspath(path_filename_disk))) != allowed_path:
            raise OSError(
                f"Path '{path_filename_disk}' is outside of the allowed directory: {allowed_path}"
            )
        if not os.path.exists(path_filename_disk.parent):
            os.makedirs(path_filename_disk.parent)
        with open(path_filename_disk, "w", encoding="utf8") as file_desc:
            file_desc.write(source_code["content"])

    remappings = dict_source_code.get("settings", {}).get("remappings", None)

    return list(filtered_paths), directory, sanitize_remappings(remappings, directory)


def sanitize_remappings(remappings: list[str] | None, allowed_directory: str) -> list[str] | None:
    """Sanitize a list of remappings, rejecting any that escape the allowed directory.

    Args:
        remappings: (Optional[List[str]]): a list of remappings.
        allowed_directory: the allowed base directory for remap destinations.

    Returns:
        Optional[List[str]]: a list of sanitized remappings.
    """
    if remappings is None:
        return remappings

    allowed_path = os.path.abspath(allowed_directory)

    remappings_clean: list[str] = []
    for r in remappings:
        split = r.split("=", 2)
        if len(split) != 2:
            LOGGER.warning("Invalid remapping %s", r)
            continue

        origin, dest = split[0], PurePosixPath(split[1])

        if dest.is_absolute():
            dest = PurePosixPath(*dest.parts[1:])

        dest_disk = Path(allowed_directory, dest)

        if os.path.commonpath((allowed_path, os.path.abspath(dest_disk))) != allowed_path:
            LOGGER.warning("Remapping %s=%s is potentially unsafe, skipping", origin, dest)
            continue

        # always use a trailing slash for the destination
        remappings_clean.append(f"{origin}={str(dest / '_')[:-1]}")

    return remappings_clean
