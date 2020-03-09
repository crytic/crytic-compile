"""
Module handling the cli arguments
"""
from argparse import ArgumentParser

from crytic_compile.cryticparser import DEFAULTS_FLAG_IN_CONFIG


def init(parser: ArgumentParser):
    """
    Add crytic-compile arguments to the parser

    :param parser:
    :return:
    """

    group_solc = parser.add_argument_group("Compile options")
    group_solc.add_argument(
        "--compile-force-framework",
        help="Force the compile to a given framework "
        "(truffle, embark, dapp, etherlime, etherscan, waffle)",
        action="store",
        default=DEFAULTS_FLAG_IN_CONFIG["compile_force_framework"],
    )

    group_solc.add_argument(
        "--compile-remove-metadata",
        help="Remove the metadata from the bytecodes",
        action="store_true",
        default=DEFAULTS_FLAG_IN_CONFIG["compile_remove_metadata"],
    )

    group_solc.add_argument(
        "--compile-custom-build",
        help="Replace platform specific build command",
        action="store",
        default=DEFAULTS_FLAG_IN_CONFIG["compile_custom_build"],
    )

    group_solc.add_argument(
        "--ignore-compile",
        help="Do not run compile of any platform",
        action="store_true",
        dest="ignore_compile",
        default=DEFAULTS_FLAG_IN_CONFIG["ignore_compile"],
    )

    _init_solc(parser)
    _init_truffle(parser)
    _init_embark(parser)
    _init_dapp(parser)
    _init_etherlime(parser)
    _init_etherscan(parser)
    _init_waffle(parser)
    _init_npx(parser)


def _init_solc(parser):
    group_solc = parser.add_argument_group("Solc options")
    group_solc.add_argument(
        "--solc", help="solc path", action="store", default=DEFAULTS_FLAG_IN_CONFIG["solc"]
    )

    group_solc.add_argument(
        "--solc-remaps",
        help="Add remapping",
        action="store",
        default=DEFAULTS_FLAG_IN_CONFIG["solc_remaps"],
    )

    group_solc.add_argument(
        "--solc-args",
        help="Add custom solc arguments. Example: --solc-args"
        ' "--allow-path /tmp --evm-version byzantium".',
        action="store",
        default=DEFAULTS_FLAG_IN_CONFIG["solc_args"],
    )

    group_solc.add_argument(
        "--solc-disable-warnings",
        help="Disable solc warnings",
        action="store_true",
        default=DEFAULTS_FLAG_IN_CONFIG["solc_disable_warnings"],
    )

    group_solc.add_argument(
        "--solc-working-dir",
        help="Change the default working directory",
        action="store",
        default=DEFAULTS_FLAG_IN_CONFIG["solc_working_dir"],
    )

    group_solc.add_argument(
        "--solc-solcs-select",
        help="Specify different solc version to try (env config). Depends on solc-select    ",
        action="store",
        default=DEFAULTS_FLAG_IN_CONFIG["solc_solcs_select"],
    )

    group_solc.add_argument(
        "--solc-solcs-bin",
        help="Specify different solc version to try (path config)."
        " Example: --solc-solcs-bin solc-0.4.24,solc-0.5.3",
        action="store",
        default=DEFAULTS_FLAG_IN_CONFIG["solc_solcs_bin"],
    )

    group_solc.add_argument(
        "--solc-standard-json",
        help="Compile all specified targets in a single compilation using solc standard json",
        action="store_true",
        default=DEFAULTS_FLAG_IN_CONFIG["solc_standard_json"],
    )


def _init_waffle(parser):
    group_waffle = parser.add_argument_group("Waffle options")
    group_waffle.add_argument(
        "--waffle-ignore-compile",
        help="Do not run waffle compile",
        action="store_true",
        dest="waffle_ignore_compile",
        default=DEFAULTS_FLAG_IN_CONFIG["waffle_ignore_compile"],
    )

    group_waffle.add_argument(
        "--waffle-config-file",
        help="Provide a waffle config file",
        action="store",
        default=DEFAULTS_FLAG_IN_CONFIG["waffle_config_file"],
    )


def _init_truffle(parser):
    group_truffle = parser.add_argument_group("Truffle options")
    group_truffle.add_argument(
        "--truffle-ignore-compile",
        help="Do not run truffle compile",
        action="store_true",
        dest="truffle_ignore_compile",
        default=DEFAULTS_FLAG_IN_CONFIG["truffle_ignore_compile"],
    )

    group_truffle.add_argument(
        "--truffle-build-directory",
        help="Use an alternative truffle build directory",
        action="store",
        dest="truffle_build_directory",
        default=DEFAULTS_FLAG_IN_CONFIG["truffle_build_directory"],
    )

    group_truffle.add_argument(
        "--truffle-version",
        help="Use a local Truffle version (with npx)",
        action="store",
        default=DEFAULTS_FLAG_IN_CONFIG["truffle_version"],
    )
    return group_truffle


def _init_embark(parser):
    group_embark = parser.add_argument_group("Embark options")
    group_embark.add_argument(
        "--embark-ignore-compile",
        help="Do not run embark build",
        action="store_true",
        dest="embark_ignore_compile",
        default=DEFAULTS_FLAG_IN_CONFIG["embark_ignore_compile"],
    )

    group_embark.add_argument(
        "--embark-overwrite-config",
        help="Install @trailofbits/embark-contract-export and add it to embark.json",
        action="store_true",
        default=DEFAULTS_FLAG_IN_CONFIG["embark_overwrite_config"],
    )


def _init_brownie(parser):
    group_embark = parser.add_argument_group("Brownie options")
    group_embark.add_argument(
        "--brownie-ignore-compile",
        help="Do not run brownie compile",
        action="store_true",
        dest="brownie_ignore_compile",
        default=DEFAULTS_FLAG_IN_CONFIG["brownie_ignore_compile"],
    )


def _init_dapp(parser):
    group_dapp = parser.add_argument_group("Dapp options")
    group_dapp.add_argument(
        "--dapp-ignore-compile",
        help="Do not run dapp build",
        action="store_true",
        dest="dapp_ignore_compile",
        default=DEFAULTS_FLAG_IN_CONFIG["dapp_ignore_compile"],
    )


def _init_etherlime(parser):
    group_etherlime = parser.add_argument_group("Etherlime options")
    group_etherlime.add_argument(
        "--etherlime-ignore-compile",
        help="Do not run etherlime compile",
        action="store_true",
        dest="etherlime_ignore_compile",
        default=DEFAULTS_FLAG_IN_CONFIG["etherlime_ignore_compile"],
    )

    group_etherlime.add_argument(
        "--etherlime-compile-arguments",
        help="Add arbitrary arguments to etherlime compile "
        "(note: [dir] is the the directory provided to crytic-compile)",
        action="store_true",
        dest="etherlime_compile_arguments",
        default=DEFAULTS_FLAG_IN_CONFIG["etherlime_compile_arguments"],
    )


def _init_etherscan(parser):
    group_etherscan = parser.add_argument_group("Etherscan options")
    group_etherscan.add_argument(
        "--etherscan-only-source-code",
        help="Only compile if the source code is available.",
        action="store_true",
        dest="etherscan_only_source_code",
        default=DEFAULTS_FLAG_IN_CONFIG["etherscan_only_source_code"],
    )

    group_etherscan.add_argument(
        "--etherscan-only-bytecode",
        help="Only looks for bytecode.",
        action="store_true",
        dest="etherscan_only_bytecode",
        default=DEFAULTS_FLAG_IN_CONFIG["etherscan_only_bytecode"],
    )

    group_etherscan.add_argument(
        "--etherscan-apikey",
        help="Etherscan API key.",
        action="store",
        dest="etherscan_api_key",
        default=DEFAULTS_FLAG_IN_CONFIG["etherscan_api_key"],
    )


def _init_npx(parser):
    group_npx = parser.add_argument_group("NPX options")
    group_npx.add_argument(
        "--npx-disable",
        help="Do not use npx",
        action="store_true",
        dest="npx_disable",
        default=DEFAULTS_FLAG_IN_CONFIG["npx_disable"],
    )
