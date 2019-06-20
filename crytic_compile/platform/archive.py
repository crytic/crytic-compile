import os
import logging

from .types import Type
logger = logging.getLogger("CryticCompile")

DEPENDENCIES = {}


def compile(crytic_compile, target, **kwargs):
    crytic_compile.type = Type.ARCHIVE


def is_solc(target):
    return os.path.isfile(target) and target.endswith('.sol')


def is_dependency(_path):
    return DEPENDENCIES[_path]


def set_dependency_status(_path, status):
    DEPENDENCIES[_path] = status


def _relative_to_short(relative):
    return relative
