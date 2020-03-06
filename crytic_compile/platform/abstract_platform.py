"""
Abstract Platform
"""
import abc
from typing import TYPE_CHECKING, List

from crytic_compile.platform import Type
from crytic_compile.utils.unit_tests import guess_tests

if TYPE_CHECKING:
    from crytic_compile import CryticCompile


class IncorrectPlatformInitialization(Exception):
    """
    Exception raises if a platform was not properly defined
    """

    pass


class AbstractPlatform(metaclass=abc.ABCMeta):
    """
    This is the abstract class for the platform
    """

    NAME: str = ""
    PROJECT_URL: str = ""
    TYPE: Type = Type.NOT_IMPLEMENTED

    HIDE = False  # True if the class is not meant for direct user manipulation

    def __init__(self, target: str, **kwargs: str):
        if not self.NAME:
            raise IncorrectPlatformInitialization(
                "NAME is not initialized {}".format(self.__class__.__name__)
            )

        if not self.PROJECT_URL:
            raise IncorrectPlatformInitialization(
                "PROJECT_URL is not initialized {}".format(self.__class__.__name__)
            )

        if self.TYPE == Type.NOT_IMPLEMENTED:
            raise IncorrectPlatformInitialization(
                "TYPE is not initialized {}".format(self.__class__.__name__)
            )

        self._target: str = target

    # region Properties.
    ###################################################################################
    ###################################################################################
    # The properties might be different from the class value
    # For example the archive will return the underlying platform values
    @property
    def target(self) -> str:
        """
        Return the target name

        :return:
        """
        return self._target

    @property
    def platform_name_used(self) -> str:
        """
        Return the underlying platform used

        :return:
        """
        return self.NAME

    @property
    def platform_project_url_used(self) -> str:
        """
        Return the underlying platform url used

        :return:
        """
        return self.PROJECT_URL

    @property
    def platform_type_used(self) -> Type:
        """
        Return the underlying platform url used

        :return:
        """
        return self.TYPE

    # endregion
    ###################################################################################
    ###################################################################################
    # region Abstract methods
    ###################################################################################
    ###################################################################################

    @abc.abstractmethod
    def compile(self, crytic_compile: "CryticCompile", **kwargs: str):
        """
        Run the compilation

        :param crytic_compile:
        :param kwargs:
        :return:
        """
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

    # Only _guessed_tests is an abstract method
    # guessed_tests will call the generic guess_tests and appends to the list
    # platforms-dependent tests
    @abc.abstractmethod
    def _guessed_tests(self) -> List[str]:
        """
        Guess the potential unit tests commands

        :return:
        """
        return []

    def guessed_tests(self) -> List[str]:
        """
        Guess the potential unit tests commands

        :return: list of unit tests command guessed
        """
        return guess_tests(self._target) + self._guessed_tests()

    # endregion
    ###################################################################################
    ###################################################################################
