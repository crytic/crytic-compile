"""Handle the compiler version"""

import logging

from solc_select.solc_select import install_artifacts, installed_versions

LOGGER = logging.getLogger("CryticCompile")


# pylint: disable=too-few-public-methods
class CompilerVersion:
    """
    Class representing the compiler information
    """

    def __init__(
        self,
        compiler: str,
        version: str | None,
        optimized: bool | None,
        optimize_runs: int | None = None,
    ) -> None:
        """
        Initialize a compier version object

        Args:
            compiler (str): compiler (in most of the case use "solc")
            version (str): compiler version
            optimized (Optional[bool]): true if optimization are enabled
            optimize_runs (Optional[int]): optimize runs number
        """
        self.compiler: str = compiler
        self.version: str | None = version
        self.optimized: bool | None = optimized
        self.optimize_runs: int | None = optimize_runs

    def look_for_installed_version(self) -> None:
        """
        This function queries solc-select to see if the current compiler version is installed
        And if its not it will install it

        Returns:

        """
        if self.version is not None and self.version not in installed_versions():
            # TODO: check that the solc version was installed.
            # Blocked by https://github.com/crytic/solc-select/issues/143
            install_artifacts([self.version])
