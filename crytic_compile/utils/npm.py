import json
from pathlib import Path
from typing import Union, List


def get_package_name(target_txt: Union[str, List]) -> Union[str, None]:
    """
    Return the package's name
    :param target:
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
            with open(package) as f:
                try:
                    package_dict = json.load(f)
                    return package_dict.get("name", None)
                except json.JSONDecodeError:
                    return None
    return None
