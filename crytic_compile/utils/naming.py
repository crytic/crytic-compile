import os


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

