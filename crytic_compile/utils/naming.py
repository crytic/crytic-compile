import platform
from pathlib import Path, PureWindowsPath
from ..platform.exceptions import InvalidCompilation


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


def convert_filename(filename):
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

    return str(filename)
