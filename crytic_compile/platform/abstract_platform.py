"""
Abstract Platform

This gives the skeleton for any platform supported by crytic-compile
"""
import abc
from typing import TYPE_CHECKING, List, Dict

from crytic_compile.platform import Type
from crytic_compile.utils.unit_tests import guess_tests

if TYPE_CHECKING:
    from crytic_compile import CryticCompile


class IncorrectPlatformInitialization(Exception):
    """
    Exception raises if a platform was not properly defined
    """

    # pylint: disable=unnecessary-pass
    pass


class AbstractPlatform(metaclass=abc.ABCMeta):
    """
    This is the abstract class for the platform
    """

    NAME: str = ""
    PROJECT_URL: str = ""
    TYPE: Type = Type.NOT_IMPLEMENTED

    HIDE = False  # True if the class is not meant for direct user manipulation

    def __init__(self, target: str, **_kwargs: str):
        """Init the object

        Args:
            target (str): path to the target
            **_kwargs: optional arguments.

        Raises:
            IncorrectPlatformInitialization: If the Platform was not correctly designed
        """
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
        self._cached_dependencies: Dict[str, bool] = dict()

    # region Properties.
    ###################################################################################
    ###################################################################################
    # The properties might be different from the class value
    # For example the archive will return the underlying platform values
    @property
    def target(self) -> str:
        """Return the target name

        Returns:
            str: The target name
        """
        return self._target

    @property
    def platform_name_used(self) -> str:
        """Return the name of the underlying platform used

        Returns:
            str: The name of the underlying platform used
        """
        return self.NAME

    @property
    def platform_project_url_used(self) -> str:
        """Return the underlying platform project 's url

        Returns:
            str: Underlying platform project 's url
        """
        return self.PROJECT_URL

    @property
    def platform_type_used(self) -> Type:
        """Return the type of the underlying platform used

        Returns:
            Type: [description]
        """
        return self.TYPE

    # endregion
    ###################################################################################
    ###################################################################################
    # region Abstract methods
    ###################################################################################
    ###################################################################################

    @abc.abstractmethod
    def compile(self, crytic_compile: "CryticCompile", **kwargs: str) -> None:
        """Run the compilation

        Args:
            crytic_compile (CryticCompile): CryticCompile object associated with the platform
            **kwargs: optional arguments.
        """
        return

    @staticmethod
    @abc.abstractmethod
    def is_supported(target: str, **kwargs: str) -> bool:
        """Check if the target is a project supported by this platform

        Args:
            target (str): path to the target
            **kwargs: optional arguments. Used: "dapp_ignore"

        Returns:
            bool: True if the target is supported
        """
        return False

    @abc.abstractmethod
    def is_dependency(self, path: str) -> bool:
        """Check if the target is a dependency

        Args:
            path (str): path to the target

        Returns:
            bool: True if the target is a dependency
        """
        return False

    # Only _guessed_tests is an abstract method
    # guessed_tests will call the generic guess_tests and appends to the list
    # platforms-dependent tests
    @abc.abstractmethod
    def _guessed_tests(self) -> List[str]:
        """Guess the potential unit tests commands

        Returns:
            List[str]: list of potential unit tests commands
        """
        return []

    def guessed_tests(self) -> List[str]:
        """Guess the potential unit tests commands

        Returns:
            List[str]: list of potential unit tests commands
        """
        return guess_tests(self._target) + self._guessed_tests()

    # endregion
    ###################################################################################
    ###################################################################################
