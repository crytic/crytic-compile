"""
Natspec module https://solidity.readthedocs.io/en/latest/natspec-format.html
"""
from typing import Optional, List, Dict


class UserMethod:

    def __init__(self, method):
        self._notice: Optional[str] = method.get('notice', None)

    @property
    def notice(self):
        """
        Return the method notice
        :return: Optional[str]
        """
        return self._notice

    def export(self):
        """
        Export to a python dict
        :return: Dict
        """
        return {"notice": self.notice}


class DevMethod:

    def __init__(self, method):
        self._author: Optional[str] = method.get('author', None)
        self._details: Optional[str] = method.get('details', None)
        self._params: Dict[str, str] = method.get('params', {})
        self._return: Optional[str] = method.get('return', None)

    @property
    def author(self):
        """
        Return the method author
        :return: Optional[str]
        """
        return self._author

    @property
    def details(self):
        """
        Return the method details
        :return: Optional[str]
        """
        return self._details

    @property
    def method_return(self):
        """
        Return the method return
        :return: Optional[str]
        """
        return self._return

    @property
    def params(self):
        """
        Return the method params
        :return: Dict[str, str]
        """
        return self._params

    def export(self):
        """
        Export to a python dict
        :return: Dict
        """
        return {"author": self.author,
                "details": self.details,
                "params": self.params,
                "return": self.method_return}


class UserDoc:
    def __init__(self, userdoc: dict):
        self._notice: Optional[str] = userdoc.get('notice', None)
        self._methods: Dict[str, UserMethod] = {k: UserMethod(item) for k, item in userdoc.get('methods', {}).items()}

    @property
    def notice(self):
        """
        Return the user notice
        :return: Optional[str]
        """
        return self._notice

    @property
    def methods(self):
        """
        Return the user methods
        :return: Dict[str, UserMethod]
        """
        return self._methods

    def export(self):
        """
        Export to a python dict
        :return: Dict
        """
        return {"methods": {k: items.export() for k, items in self.methods.items()},
                "notice": self.notice}


class DevDoc:
    def __init__(self, devdoc: Dict):
        self._author: Optional[str] = devdoc.get('author', None)
        self._details: Optional[str] = devdoc.get('details', None)
        self._methods: Dict[str, DevMethod] = {k: DevMethod(item) for k, item in devdoc.get('methods', {}).items()}
        self._title: Optional[str] = devdoc.get('title', None)

    @property
    def author(self):
        """
        Return the dev author
        :return: Optional[str]
        """
        return self._author

    @property
    def details(self):
        """
        Return the dev details
        :return: Optional[str]
        """
        return self._details

    @property
    def methods(self):
        """
         Return the dev methods
         :return: Dict[str, DevMethod]
         """
        return self._methods

    @property
    def title(self):
        """
        Return the dev title
        :return: Optional[str]
        """
        return self._title

    def export(self):
        """
        Export to a python dict
        :return: Dict
        """
        return {"methods": {k: items.export() for k, items in self.methods.items()},
                "author": self.author,
                "details": self.details,
                "title": self.title}


class Natspec:

    def __init__(self, userdoc: Dict, devdoc: Dict):
        self._userdoc: UserDoc = UserDoc(userdoc)
        self._devdoc: DevDoc = DevDoc(devdoc)

    @property
    def userdoc(self):
        """
        Return the userdoc
        :return: UserDoc
        """
        return self._userdoc

    @property
    def devdoc(self):
        """
        Return the devdoc
        :return: DevDoc
        """
        return self._devdoc
