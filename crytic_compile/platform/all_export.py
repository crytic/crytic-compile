"""
Module containing all the supported export functions
"""
from crytic_compile.platform.archive import export_to_archive
from crytic_compile.platform.solc import export_to_solc
from crytic_compile.platform.standard import export_to_standard

PLATFORMS_EXPORT = {
    "standard": export_to_standard,
    "crytic-compile": export_to_standard,
    "solc": export_to_solc,
    "archive": export_to_archive,
}
