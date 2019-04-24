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

    if not filename.exists():
        if Path('node_modules').joinpath(filename).exists():
            filename = Path.cwd().joinpath('node_modules', filename)
        if Path('contracts').joinpath(filename).exists():
            filename = Path.cwd().joinpath('contracts', filename)
        elif working_dir and Path(working_dir).joinpath(filename).exists():
            filename = Path(working_dir).joinpath(filename)
        else:
            raise InvalidCompilation(f'Unknown file: {filename}')
    elif not filename.is_absolute():
        filename = Path.cwd().joinpath(filename)

    absolute = filename
    relative = Path(os.path.relpath(filename, Path.cwd()))

    short = relative_to_short(relative)


    return Filename(absolute=str(absolute),
                    relative=str(relative),
                    short=str(short),
                    used=used_filename)
