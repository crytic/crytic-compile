"""
Module handling the file naming operation (relative -> absolute, etc)
"""

import logging
import os.path
import platform
from collections import namedtuple
from pathlib import Path
from typing import TYPE_CHECKING, Tuple, Union, Callable, Optional

from crytic_compile.platform.exceptions import InvalidCompilation

# Cycle dependency
if TYPE_CHECKING:
    from crytic_compile import CryticCompile

LOGGER = logging.getLogger("CryticCompile")

Filename = namedtuple("Filename", ["absolute", "used", "relative", "short"])


def extract_name(name: str) -> str:
    """Convert '/path:Contract' to Contract

    Args:
        name (str): name to convert

    Returns:
        str: extracted contract name
    """
    return name[name.rfind(":") + 1 :]


def extract_filename(name: str) -> str:
    """Convert '/path:Contract' to /path

    Args:
        name (str): name to convert

    Returns:
        str: extracted filename
    """
    if not ":" in name:
        return name
    return name[: name.rfind(":")]


def combine_filename_name(filename: str, name: str) -> str:
    """Combine the filename with the contract name

    Args:
        filename (str): filename
        name (str): contract name

    Returns:
        str: Combined names
    """
    return filename + ":" + name


# pylint: disable=too-many-branches
def convert_filename(
    used_filename: Union[str, Path],
    relative_to_short: Callable[[Path], Path],
    crytic_compile: "CryticCompile",
    working_dir: Optional[Union[str, Path]] = None,
    node_modules_dir: Optional[Union[str, Path]] = None
) -> Filename:
    """Convert a filename to CryticCompile Filename object.
    The used_filename can be absolute, relative, or missing node_modules/contracts directory

    Args:
        used_filename (Union[str, Path]): Used filename
        relative_to_short (Callable[[Path], Path]): Callback to translate the relative to short
        crytic_compile (CryticCompile): Associated CryticCompile object
        working_dir (Optional[Union[str, Path]], optional): Working directory. Defaults to None.
        node_modules_dir (Optional[Union[str, Path]], optional): node_modules directory.
            Defaults to None.

    Raises:
        InvalidCompilation: [description]

    Returns:
        Filename: Filename converted
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

    working_dir, cwd, node_modules_dir = _get_working_directories(working_dir, node_modules_dir)

    if crytic_compile.package_name:
        try:
            filename = filename.relative_to(Path(crytic_compile.package_name))
        except ValueError:
            pass
    if not filename.exists():
        if node_modules_dir.joinpath(filename).exists():
            filename = node_modules_dir.joinpath(filename)
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
        absolute=str(absolute),
        relative=relative.as_posix(),
        short=short.as_posix(),
        used=used_filename,
    )

def _get_working_directories(
    working_dir: Optional[Union[str, Path]],
    node_modules_dir: Optional[Union[str, Path]]
) -> Tuple[Path, Path, Path]:
    """Checks input directories and returns processed paths ready to use.

    Args:
        working_dir (Optional[Union[str, Path]], optional): Working directory.
        node_modules_dir (Optional[Union[str, Path]], optional): node_modules directory..

    Returns:
        Tuple[Path, Path, Path]: Working directory, current working directory and node_modules
            directory.
    """
    if working_dir is None:
        cwd = Path.cwd()
        working_dir = cwd
    else:
        working_dir = Path(working_dir)
        if working_dir.is_absolute():
            cwd = working_dir
        else:
            cwd = Path.cwd().joinpath(Path(working_dir)).resolve()

    if node_modules_dir is None:
        node_modules_dir = cwd.joinpath(Path("node_modules"))
    else:
        node_modules_dir = Path(node_modules_dir)

    return working_dir, cwd, node_modules_dir
