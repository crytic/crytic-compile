"""
This is the Slither cli script
"""
import argparse
import json
import logging
import os
import sys

from pkg_resources import require

from crytic_compile.crytic_compile import compile_all, get_platforms
from crytic_compile.cryticparser import cryticparser, DEFAULTS_FLAG_IN_CONFIG
from crytic_compile.platform import InvalidCompilation
from crytic_compile.utils.zip import save_to_zip

logging.basicConfig()
LOGGER = logging.getLogger("CryticCompile")
LOGGER.setLevel(logging.INFO)


def parse_args():
    """
    Parse the arguments

    :return:
    """
    # Create our argument parser
    parser = argparse.ArgumentParser(
        description="""crytic-compile. For usage information,
see https://github.com/crytic/crytic-compile/wiki/Usage""",
        usage="crytic-compile contract.sol [flag]",
    )

    # Add arguments
    parser.add_argument("target", help="contract.sol")

    parser.add_argument(
        "--config-file",
        help="Provide a config file (default: crytic_compile.config.json)",
        action="store",
        dest="config_file",
        default="crytic_compile.config.json",
    )

    parser.add_argument(
        "--export-format",
        help="""Export json with non crytic-compile format
(default None. Accepted: standard, solc, truffle)""",
        action="store",
        dest="export_format",
        default=None,
    )

    parser.add_argument(
        "--export-formats",
        help="Comma-separated list of export format, defaults to None",
        action="store",
        dest="export_formats",
        default=None,
    )

    parser.add_argument(
        "--export-dir",
        help="Export directory (default: crytic-export)",
        action="store",
        dest="export_dir",
        default="crytic-export",
    )

    parser.add_argument(
        "--export-zip",
        help="Export all the projects to a zip file",
        action="store",
        dest="export_to_zip",
        default=None,
    )

    parser.add_argument(
        "--print-filenames",
        help="Print all the filenames",
        action="store_true",
        dest="print_filename",
        default=False,
    )

    parser.add_argument(
        "--version",
        help="displays the current version",
        version=require("crytic-compile")[0].version,
        action="version",
    )

    parser.add_argument(
        "--supported-platforms",
        help="Shows the platforms supported",
        action=ShowPlatforms,
        nargs=0,
        default=False,
    )

    cryticparser.init(parser)
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    # If there is a config file provided, update the values with the one in the config file
    if os.path.isfile(args.config_file):
        try:
            with open(args.config_file, encoding="utf8") as f_config:
                config = json.load(f_config)
                for key, elem in config.items():
                    if key not in DEFAULTS_FLAG_IN_CONFIG:
                        LOGGER.info("%s has an unknown key: %s : %s", args.config_file, key, elem)
                        continue
                    if getattr(args, key) == DEFAULTS_FLAG_IN_CONFIG[key]:
                        setattr(args, key, elem)
        except json.decoder.JSONDecodeError as exception:
            LOGGER.error(
                "Impossible to read %s, please check the file %s", args.config_file, exception
            )

    return args


class ShowPlatforms(argparse.Action):
    """
    This class is used to print the different platforms supported to the log
    See --supported-platforms
    """

    def __call__(self, parser, args, values, option_string=None):
        platforms = get_platforms()
        LOGGER.info("\n" + "\n".join([f"- {x.NAME}: {x.PROJECT_URL}" for x in platforms]))
        parser.exit()


def main():
    """
    Main function run from the cli

    :return:
    """
    args = parse_args()
    try:
        # Compile all specified (possibly glob patterned) targets.
        compilations = compile_all(**vars(args))

        # Perform relevant tasks for each compilation
        printed_filenames = set()
        for compilation in compilations:
            # Print the filename of each contract (no duplicates).
            if args.print_filename:
                for contract in compilation.contracts_names:
                    filename = compilation.filename_of_contract(contract)
                    unique_id = f"{contract} - {filename}"
                    if unique_id not in printed_filenames:
                        print(f"{contract} -> \n\tAbsolute: {filename.absolute}")
                        print(f"\tRelative: {filename.relative}")
                        print(f"\tShort: {filename.short}")
                        print(f"\tUsed: {filename.used}")
                        printed_filenames.add(unique_id)
            if args.export_format:
                compilation.export(**vars(args))

            if args.export_formats:
                for export_format in args.export_formats.split(","):
                    args.export_format = export_format
                    compilation.export(**vars(args))

        if args.export_to_zip:
            save_to_zip(compilations, args.export_to_zip)

    except InvalidCompilation as exception:
        LOGGER.error(exception)
        sys.exit(-1)


if __name__ == "__main__":
    main()
