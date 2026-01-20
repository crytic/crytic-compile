"""
Natspec module https://solidity.readthedocs.io/en/latest/natspec-format.html
"""


class UserMethod:
    """
    Model the user method
    """

    def __init__(self, method: dict | str) -> None:
        """Init the object

        Args:
            method (Union[Dict, str]): Method info (notice)
        """
        # Constructors dont have "notice: '..'"
        if isinstance(method, str):
            self._notice: str | None = method
        else:
            self._notice = method.get("notice", None)

    @property
    def notice(self) -> str | None:
        """Return the method notice

        Returns:
            Optional[str]: method notice
        """
        return self._notice

    def export(self) -> dict:
        """Export to a python dict

        Returns:
            Dict: Exported user method
        """
        return {"notice": self.notice}


class DevMethod:
    """
    Model the dev method
    """

    def __init__(self, method: dict) -> None:
        """Init the object

        Args:
            method (Dict): Method infos (author, details, params, return)
        """
        self._author: str | None = method.get("author", None)
        self._details: str | None = method.get("details", None)
        self._params: dict[str, str] = method.get("params", {})
        self._return: str | None = method.get("return", None)

    @property
    def author(self) -> str | None:
        """Return the method author

        Returns:
            Optional[str]: method author
        """
        return self._author

    @property
    def details(self) -> str | None:
        """Return the method details

        Returns:
            Optional[str]: method details
        """
        return self._details

    @property
    def method_return(self) -> str | None:
        """Return the method return

        Returns:
            Optional[str]: method return
        """
        return self._return

    @property
    def params(self) -> dict[str, str]:
        """Return the method params

        Returns:
            Dict[str, str]: method_name => params
        """
        return self._params

    def export(self) -> dict:
        """Export to a python dict

        Returns:
            Dict: Exported dev method
        """
        return {
            "author": self.author,
            "details": self.details,
            "params": self.params,
            "return": self.method_return,
        }


class UserDoc:
    """
    Model the user doc
    """

    def __init__(self, userdoc: dict):
        """Init the object

        Args:
            userdoc (dict): User doc (notice, methods)
        """
        self._notice: str | None = userdoc.get("notice", None)
        self._methods: dict[str, UserMethod] = {
            k: UserMethod(item) for k, item in userdoc.get("methods", {}).items()
        }

    @property
    def notice(self) -> str | None:
        """Return the user notice

        Returns:
            Optional[str]: user notice
        """
        return self._notice

    @property
    def methods(self) -> dict[str, UserMethod]:
        """Return the user methods

        Returns:
            Optional[str]: method_name => UserMethod
        """
        return self._methods

    def export(self) -> dict:
        """Export to a python dict

        Returns:
            Dict: Exported user doc
        """
        return {
            "methods": {k: items.export() for k, items in self.methods.items()},
            "notice": self.notice,
        }


class DevDoc:
    """
    Model the dev doc
    """

    def __init__(self, devdoc: dict):
        """Init the object

        Args:
            devdoc (Dict): dev doc (author, details, methods, title)
        """
        self._author: str | None = devdoc.get("author", None)
        self._details: str | None = devdoc.get("details", None)
        self._methods: dict[str, DevMethod] = {
            k: DevMethod(item) for k, item in devdoc.get("methods", {}).items()
        }
        self._title: str | None = devdoc.get("title", None)

    @property
    def author(self) -> str | None:
        """Return the dev author

        Returns:
            Optional[str]: dev author
        """
        return self._author

    @property
    def details(self) -> str | None:
        """Return the dev details

        Returns:
            Optional[str]: dev details
        """
        return self._details

    @property
    def methods(self) -> dict[str, DevMethod]:
        """Return the dev methods

        Returns:
            Dict[str, DevMethod]: method_name => DevMethod
        """
        return self._methods

    @property
    def title(self) -> str | None:
        """Return the dev title

        Returns:
            Optional[str]: dev title
        """
        return self._title

    def export(self) -> dict:
        """Export to a python dict

        Returns:
            Dict: Exported dev doc
        """
        return {
            "methods": {k: items.export() for k, items in self.methods.items()},
            "author": self.author,
            "details": self.details,
            "title": self.title,
        }


class Natspec:
    """
    Model natspec
    """

    def __init__(self, userdoc: dict, devdoc: dict):
        """Init the object

        Args:
            userdoc (Dict): user doc
            devdoc (Dict): dev doc
        """
        self._userdoc: UserDoc = UserDoc(userdoc)
        self._devdoc: DevDoc = DevDoc(devdoc)

    @property
    def userdoc(self) -> UserDoc:
        """Return the userdoc

        Returns:
            UserDoc: user documentation
        """
        return self._userdoc

    @property
    def devdoc(self) -> DevDoc:
        """Return the devdoc

        Returns:
            DevDoc: dev documentation
        """
        return self._devdoc
