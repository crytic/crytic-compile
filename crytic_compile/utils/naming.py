import platform
from pathlib import Path, PureWindowsPath
from collections import namedtuple
from ..platform.exceptions import InvalidCompilation


Filename = namedtuple('Filename', ['absolute', 'used', 'relative'])

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


def convert_filename(used_filename):
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
        if elements[0] == '/':
            elements = elements[1:]  # remove '/'
            elements[0] = elements[0] + ':/'  # add :/
        filename = PureWindowsPath(*elements)
    else:
        filename = Path(filename)

    if not filename.exists():
        if Path('node_modules').joinpath(filename).exists():
            filename = Path.cwd().joinpath('node_modules', filename)
        if Path('contracts').joinpath(filename).exists():
            filename = Path.cwd().joinpath('contracts', filename)
        else:
            raise InvalidCompilation(f'Unknown file: {filename}')
    elif not filename.is_absolute():
        filename = Path.cwd().joinpath(filename)

    return Filename(absolute=str(filename),
                    relative=str(filename.relative_to(Path.cwd())),
                    used=used_filename)
