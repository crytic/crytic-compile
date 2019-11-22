"""
Init module
"""

from .crytic_compile import CryticCompile, is_supported, compile_all
from .platform import InvalidCompilation
from .cryticparser import cryticparser
from .utils.zip import save_to_zip
