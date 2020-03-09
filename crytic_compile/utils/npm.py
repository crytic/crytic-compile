"""
Module handling NPM related features
"""
import json
from pathlib import Path
from typing import Union, Optional, TYPE_CHECKING

# Cycle dependency
if TYPE_CHECKING:
    from crytic_compile.platform.solc_standard_json import SolcStandardJson


def get_package_name(target_txt: Union[str, "SolcStandardJson"]) -> Optional[str]:
    """
    Return the package's name

    :param target_txt:
    :return: str or None
    """

    # Verify the target path is a string (exported zip archives are lists)
    if not isinstance(target_txt, str):
        return None

    # Obtain the path the target string represents
    target = Path(target_txt)
    if target.is_dir():
        package = Path(target, "package.json")
        if package.exists():
            with open(package) as file_desc:
                try:
                    package_dict = json.load(file_desc)
                    return package_dict.get("name", None)
                except json.JSONDecodeError:
                    return None
    return None
