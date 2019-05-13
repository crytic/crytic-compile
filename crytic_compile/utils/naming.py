import platform
import os.path
from pathlib import Path
from collections import namedtuple
from ..platform.exceptions import InvalidCompilation


Filename = namedtuple('Filename', ['absolute', 'used', 'relative', 'short'])

def extract_name(name):
    '''
        Convert '/path:Contract' to Contract
    '''
    return name[name.rfind(':')+1:]

def extract_filename(name):
    '''
        Convert '/path:Contract' to /path
    '''
    if not ':' in name:
        return name
    return name[:name.rfind(':')]

def combine_filename_name(filename, name):
    return filename + ":" + name


def convert_filename(used_filename, relative_to_short, working_dir=None):
    """
    Convert filename.
    The used_filename can be absolute, relative, or missing node_modules/contracts directory
    convert_filename return a tuple(absolute,used), where absolute points to the absolute path, and used the original
    :param used_filename:
    :param relative_to_short: lambda function
    :param working_dir:
    :return: Filename (namedtuple)
    """
    filename = used_filename
    if platform.system() == 'Windows':
        elements = list(Path(filename).parts)
        if elements[0] == '/' or elements[0] == '\\':
            elements = elements[1:]  # remove '/'
            elements[0] = elements[0] + ':/'  # add :/
        filename = Path(*elements)
    else:
        filename = Path(filename)

    if working_dir is None:
        cwd = Path.cwd()
        working_dir = cwd
    else:
        working_dir = Path(working_dir)
        if working_dir.is_absolute():
            cwd = working_dir
        else:
            cwd = Path.cwd().joinpath(Path(working_dir)).resolve()

    if not filename.exists():
        if cwd.joinpath(Path('node_modules'), filename).exists():
            filename = cwd.joinpath('node_modules', filename)
        elif cwd.joinpath(Path('contracts'), filename).exists():
            filename = cwd.joinpath('contracts', filename)
        elif working_dir.joinpath(filename).exists():
            filename = working_dir.joinpath(filename)
        else:
            raise InvalidCompilation(f'Unknown file: {filename}')
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


    return Filename(absolute=str(absolute),
                    relative=str(relative),
                    short=str(short),
                    used=used_filename)
