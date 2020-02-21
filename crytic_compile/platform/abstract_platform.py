import abc
from typing import TYPE_CHECKING, Optional

from crytic_compile.platform import Type

if TYPE_CHECKING:
    from crytic_compile import CryticCompile


class IncorrectPlatformInitialization(Exception):
    pass


class AbstractPlatform(metaclass=abc.ABCMeta):
    NAME: str = ''
    PROJECT_URL: str = ''
    TYPE: Type = Type.NOT_IMPLEMENTED

    HIDE = False  # True if the class is not meant for direct user manipulation

    def __init__(self, target: str, **kwargs: str):
        if not self.NAME:
            raise IncorrectPlatformInitialization('NAME is not initialized {}'.format(self.__class__.__name__))

        if not self.PROJECT_URL:
            raise IncorrectPlatformInitialization('PROJECT_URL is not initialized {}'.format(self.__class__.__name__))

        if self.TYPE == Type.NOT_IMPLEMENTED:
            raise IncorrectPlatformInitialization('TYPE is not initialized {}'.format(self.__class__.__name__))

        self._target: str = target

    # region Properties.
    ###################################################################################
    ###################################################################################
    # The properties might be different from the class value
    # For example the archive will return the underlying platform values
    @property
    def target(self) -> str:
        return self._target

    @property
    def platform_name_used(self):
        return self.NAME

    @property
    def platform_project_url_used(self):
        return self.PROJECT_URL

    @property
    def platform_type_used(self):
        return self.TYPE

    # endregion
    ###################################################################################
    ###################################################################################
    # region Abstract methods
    ###################################################################################
    ###################################################################################

    @abc.abstractmethod
    def compile(self, crytic_compile: "CryticCompile", **kwargs: str):
        return

    @staticmethod
    @abc.abstractmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """
        Check if the target is a project supported by this platform
        :param target:
        :return:
        """
        return False

    @abc.abstractmethod
    def is_dependency(self, path: str) -> bool:
        """
        Check if the target is a dependency
        :param path:
        :return:
        """
        return False

    # endregion
    ###################################################################################
    ###################################################################################
