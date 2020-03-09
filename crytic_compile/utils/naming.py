"""
Module handling the file naming operation (relative -> absolute, etc)
"""

import platform
import os.path
import logging
from pathlib import Path
from collections import namedtuple
from typing import TYPE_CHECKING, Union

from crytic_compile.platform.exceptions import InvalidCompilation

# Cycle dependency
if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")

Filename = namedtuple("Filename", ["absolute", "used", "relative", "short"])


def extract_name(name: str):
    """
        Convert '/path:Contract' to Contract
    """
    return name[name.rfind(":") + 1 :]


def extract_filename(name: str):
    """
        Convert '/path:Contract' to /path
    """
    if not ":" in name:
        return name
    return name[: name.rfind(":")]


def combine_filename_name(filename: str, name: str):
    """
    Combine the filename with the contract name

    :param filename:
    :param name:
    :return:
    """
    return filename + ":" + name


def convert_filename(
    used_filename: Union[str, Path],
    relative_to_short,
    crytic_compile: "CryticCompile",
    working_dir=None,
) -> Filename:
    """
    Convert filename.
    The used_filename can be absolute, relative, or missing node_modules/contracts directory
    convert_filename return a tuple(absolute,used),
    where absolute points to the absolute path, and used the original

    :param used_filename:
    :param relative_to_short: lambda function
    :param crytic_compile:
    :param working_dir:
    :return: Filename (namedtuple)
    """
    filename_txt = used_filename
    if platform.system() == "Windows":
        elements = list(Path(filename_txt).parts)
        if elements[0] == "/" or elements[0] == "\\":
            elements = elements[1:]  # remove '/'
            elements[0] = elements[0] + ":/"  # add :/
        filename = Path(*elements)
    else:
        filename = Path(filename_txt)

    if working_dir is None:
        cwd = Path.cwd()
        working_dir = cwd
    else:
        working_dir = Path(working_dir)
        if working_dir.is_absolute():
            cwd = working_dir
        else:
            cwd = Path.cwd().joinpath(Path(working_dir)).resolve()

    if crytic_compile.package_name:
        try:
            filename = filename.relative_to(Path(crytic_compile.package_name))
        except ValueError:
            pass

    if not filename.exists():
        if cwd.joinpath(Path("node_modules"), filename).exists():
            filename = cwd.joinpath("node_modules", filename)
        elif cwd.joinpath(Path("contracts"), filename).exists():
            filename = cwd.joinpath("contracts", filename)
        elif working_dir.joinpath(filename).exists():
            filename = working_dir.joinpath(filename)
        else:
            raise InvalidCompilation(f"Unknown file: {filename}")
    elif not filename.is_absolute():
        filename = cwd.joinpath(filename)

    absolute = filename
    relative = Path(os.path.relpath(filename, Path.cwd()))

    # Build the short path
    try:
        if working_dir.is_absolute():
            short = absolute.relative_to(working_dir)
        else:
            short = relative.relative_to(working_dir)
    except ValueError:
        short = relative
    except RuntimeError:
        short = relative

    short = relative_to_short(short)

    return Filename(
        absolute=str(absolute), relative=str(relative), short=str(short), used=used_filename
    )
