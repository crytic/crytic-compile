"""Handle the compiler version
"""
import logging
from typing import Optional

LOGGER = logging.getLogger("CryticCompile")

# pylint: disable=too-few-public-methods
class CompilerVersion:
    """
    Class representing the compiler information
    """

    def __init__(
        self,
        compiler: str,
        version: Optional[str],
        optimized: Optional[bool],
        optimize_runs: Optional[int] = None,
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
        self.version: Optional[str] = version
        self.optimized: Optional[bool] = optimized
        self.optimize_runs: Optional[int] = optimize_runs

    def look_for_installed_version(self) -> None:
        """
        This function queries solc-select to see if the current compiler version is installed
        And if its not it will install it

        Returns:

        """

        # pylint: disable=import-outside-toplevel
        try:
            from solc_select import solc_select

            if self.version not in solc_select.installed_versions():
                solc_select.install_artifacts([self.version])

        except ImportError:
            LOGGER.info(
                'solc-select is not installed.\nRun "pip install solc-select" to enable automatic switch of solc versions'
            )
