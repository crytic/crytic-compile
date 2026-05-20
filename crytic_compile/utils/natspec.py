"""
Natspec module https://solidity.readthedocs.io/en/latest/natspec-format.html
"""


class DevStateVariable:
    """
    Model the dev state variable
    """

    def __init__(self, variable: dict) -> None:
        """Init the object

        Args:
            method (Dict): Method infos (details, params, returns, custom:*)
        """
        self._details: str | None = variable.get("details", None)
        if "returns" in variable:
            self._returns: dict[str, str] = variable["returns"]
        elif "return" in variable:
            self._returns: dict[str, str] = {"_0": variable["return"]}
        else:
            self._returns: dict[str, str] = {}
        # Extract custom fields (keys starting with "custom:")
        self._custom: dict[str, str] = {
            k: v for k, v in variable.items() if k.startswith("custom:")
        }

    @property
    def details(self) -> str | None:
        """Return the state variable details

        Returns:
            Optional[str]: state variable details
        """
        return self._details

    @property
    def variable_returns(self) -> dict[str, str]:
        """Return the state variable returns

        Returns:
            dict[str, str]: state variable returns
        """
        return self._returns

    @property
    def custom(self) -> dict[str, str]:
        """Return the state variable custom fields

        Returns:
            Dict[str, str]: custom field name => value (e.g. "custom:security" => "value")
        """
        return self._custom

    def export(self) -> dict:
        """Export to a python dict

        Returns:
            Dict: Exported dev state variable
        """
        result = {
            "details": self.details,
            "returns": self.variable_returns,
            "custom": self.custom,
        }
        return result


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
            method (Dict): Method infos (author, details, params, returns, custom:*)
        """
        self._author: str | None = method.get("author", None)
        self._details: str | None = method.get("details", None)
        self._params: dict[str, str] = method.get("params", {})
        if "returns" in method:
            self._returns: dict[str, str] = method["returns"]
        elif "return" in method:
            self._returns: dict[str, str] = {"_0": method["return"]}
        else:
            self._returns: dict[str, str] = {}
        # Extract custom fields (keys starting with "custom:")
        self._custom: dict[str, str] = {k: v for k, v in method.items() if k.startswith("custom:")}

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
    def method_returns(self) -> dict[str, str]:
        """Return the method returns

        Returns:
            dict[str, str]: method returns
        """
        return self._returns

    @property
    def params(self) -> dict[str, str]:
        """Return the method params

        Returns:
            Dict[str, str]: method_name => params
        """
        return self._params

    @property
    def custom(self) -> dict[str, str]:
        """Return the method custom fields

        Returns:
            Dict[str, str]: custom field name => value (e.g. "custom:security" => "value")
        """
        return self._custom

    def export(self) -> dict:
        """Export to a python dict

        Returns:
            Dict: Exported dev method
        """
        result = {
            "author": self.author,
            "details": self.details,
            "params": self.params,
            "returns": self.method_returns,
        }
        # Include custom fields if present
        result.update(self.custom)
        return result


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
            devdoc (Dict): dev doc (author, details, methods, title, custom:*)
        """
        self._author: str | None = devdoc.get("author", None)
        self._details: str | None = devdoc.get("details", None)
        self._methods: dict[str, DevMethod] = {
            k: DevMethod(item) for k, item in devdoc.get("methods", {}).items()
        }
        self._state_variables: dict[str, DevStateVariable] = {
            k: DevStateVariable(item) for k, item in devdoc.get("stateVariables", {}).items()
        }
        self._title: str | None = devdoc.get("title", None)
        # Extract contract-level custom fields (keys starting with "custom:")
        self._custom: dict[str, str] = {k: v for k, v in devdoc.items() if k.startswith("custom:")}

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
    def state_variables(self) -> dict[str, DevStateVariable]:
        """Return the dev state variables

        Returns:
            Dict[str, DevStateVariable]: state_variable_name => DevStateVariable
        """
        return self._state_variables

    @property
    def title(self) -> str | None:
        """Return the dev title

        Returns:
            Optional[str]: dev title
        """
        return self._title

    @property
    def custom(self) -> dict[str, str]:
        """Return the contract-level custom fields

        Returns:
            Dict[str, str]: custom field name => value (e.g. "custom:security" => "value")
        """
        return self._custom

    def export(self) -> dict:
        """Export to a python dict

        Returns:
            Dict: Exported dev doc
        """
        result = {
            "methods": {k: items.export() for k, items in self.methods.items()},
            "author": self.author,
            "details": self.details,
            "title": self.title,
            "state_variables": self.state_variables,
        }
        # Include custom fields if present
        result.update(self.custom)
        return result


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
