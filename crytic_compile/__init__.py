"""
Init module
"""

from .crytic_compile import CryticCompile, compile_all, is_supported
from .cryticparser import cryticparser
from .platform import InvalidCompilation
from .utils.zip import save_to_zip
