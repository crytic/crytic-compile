"""
Test NatSpec parsing, including custom fields (@custom:*)
"""

from crytic_compile.utils.natspec import (
    DevDoc,
    DevMethod,
    DevStateVariable,
    Natspec,
    UserDoc,
    UserMethod,
)


class TestUserMethod:
    """Tests for UserMethod class"""

    def test_usermethod_notice_from_dict(self) -> None:
        """Test UserMethod parses notice from dict"""
        method = UserMethod({"notice": "This is a notice"})
        assert method.notice == "This is a notice"

    def test_usermethod_notice_from_string(self) -> None:
        """Test UserMethod parses notice from string (constructor style)"""
        method = UserMethod("Constructor notice")
        assert method.notice == "Constructor notice"

    def test_usermethod_export(self) -> None:
        """Test UserMethod export"""
        method = UserMethod({"notice": "Test notice"})
        exported = method.export()
        assert exported == {"notice": "Test notice"}


class TestDevMethod:
    """Tests for DevMethod class"""

    def test_devmethod_basic_fields(self) -> None:
        """Test DevMethod parses basic fields"""
        method_data = {
            "author": "Test Author",
            "details": "Method details",
            "params": {"a": "first param", "b": "second param"},
            "return": "return value description",
        }
        method = DevMethod(method_data)
        assert method.author == "Test Author"
        assert method.details == "Method details"
        assert method.params == {"a": "first param", "b": "second param"}
        assert method.method_returns == {"_0": "return value description"}

    def test_devmethod_custom_fields_parsing(self) -> None:
        """Test DevMethod extracts custom fields"""
        method_data = {
            "params": {"a": "param a"},
            "custom:security": "critical",
            "custom:oz-upgrades-unsafe-allow": "constructor",
        }
        method = DevMethod(method_data)
        assert method.custom == {
            "custom:security": "critical",
            "custom:oz-upgrades-unsafe-allow": "constructor",
        }

    def test_devmethod_no_custom_fields(self) -> None:
        """Test DevMethod returns empty dict when no custom fields"""
        method_data = {
            "author": "Test Author",
            "params": {"a": "param a"},
        }
        method = DevMethod(method_data)
        assert method.custom == {}

    def test_devmethod_export_includes_custom(self) -> None:
        """Test DevMethod export includes custom fields"""
        method_data = {
            "author": "Test Author",
            "details": "Details",
            "params": {"x": "param x"},
            "return": "returns something",
            "custom:security": "critical",
            "custom:audit": "passed",
        }
        method = DevMethod(method_data)
        exported = method.export()

        assert exported["author"] == "Test Author"
        assert exported["details"] == "Details"
        assert exported["params"] == {"x": "param x"}
        assert exported["returns"] == {"_0": "returns something"}
        assert exported["custom:security"] == "critical"
        assert exported["custom:audit"] == "passed"

    def test_devmethod_empty_method(self) -> None:
        """Test DevMethod with empty dict"""
        method = DevMethod({})
        assert method.author is None
        assert method.details is None
        assert method.params == {}
        assert method.method_returns == {}
        assert method.custom == {}

    def test_devmethod_returns_dict(self) -> None:
        """Test DevMethod with 'returns' dict field (multiple return values)"""
        method_data = {
            "details": "Method with multiple returns",
            "returns": {"_0": "first value", "_1": "second value"},
        }
        method = DevMethod(method_data)
        assert method.method_returns == {"_0": "first value", "_1": "second value"}

    def test_devmethod_returns_takes_precedence(self) -> None:
        """Test DevMethod prefers 'returns' over 'return' when both present"""
        method_data = {
            "returns": {"_0": "from returns"},
            "return": "from return",
        }
        method = DevMethod(method_data)
        assert method.method_returns == {"_0": "from returns"}


class TestDevStateVariable:
    """Tests for DevStateVariable class"""

    def test_state_variable_with_returns_dict(self) -> None:
        """Test DevStateVariable with 'returns' dict field"""
        var_data = {
            "details": "A state variable",
            "returns": {"_0": "the stored value"},
        }
        var = DevStateVariable(var_data)
        assert var.details == "A state variable"
        assert var.variable_returns == {"_0": "the stored value"}

    def test_state_variable_with_return_string(self) -> None:
        """Test DevStateVariable falls back to 'return' string field"""
        var_data = {
            "details": "A state variable",
            "return": "the stored value",
        }
        var = DevStateVariable(var_data)
        assert var.variable_returns == {"_0": "the stored value"}

    def test_state_variable_returns_takes_precedence(self) -> None:
        """Test DevStateVariable prefers 'returns' over 'return' when both present"""
        var_data = {
            "returns": {"_0": "from returns"},
            "return": "from return",
        }
        var = DevStateVariable(var_data)
        assert var.variable_returns == {"_0": "from returns"}

    def test_state_variable_empty(self) -> None:
        """Test DevStateVariable with empty dict"""
        var = DevStateVariable({})
        assert var.details is None
        assert var.variable_returns == {}
        assert var.custom == {}

    def test_state_variable_custom_fields(self) -> None:
        """Test DevStateVariable extracts custom fields"""
        var_data = {
            "details": "A variable",
            "custom:security": "sensitive",
            "custom:deprecated": "true",
        }
        var = DevStateVariable(var_data)
        assert var.custom == {
            "custom:security": "sensitive",
            "custom:deprecated": "true",
        }

    def test_state_variable_export(self) -> None:
        """Test DevStateVariable export"""
        var_data = {
            "details": "A state variable",
            "returns": {"_0": "the value"},
            "custom:audit": "verified",
        }
        var = DevStateVariable(var_data)
        exported = var.export()
        assert exported["details"] == "A state variable"
        assert exported["returns"] == {"_0": "the value"}
        assert exported["custom"] == {"custom:audit": "verified"}


class TestUserDoc:
    """Tests for UserDoc class"""

    def test_userdoc_basic(self) -> None:
        """Test UserDoc parses basic fields"""
        userdoc_data = {
            "notice": "Contract notice",
            "methods": {
                "test(uint256)": {"notice": "Method notice"},
            },
        }
        userdoc = UserDoc(userdoc_data)
        assert userdoc.notice == "Contract notice"
        assert "test(uint256)" in userdoc.methods
        assert userdoc.methods["test(uint256)"].notice == "Method notice"

    def test_userdoc_export(self) -> None:
        """Test UserDoc export"""
        userdoc_data = {
            "notice": "Contract notice",
            "methods": {"foo()": {"notice": "Foo notice"}},
        }
        userdoc = UserDoc(userdoc_data)
        exported = userdoc.export()
        assert exported["notice"] == "Contract notice"
        assert exported["methods"]["foo()"]["notice"] == "Foo notice"


class TestDevDoc:
    """Tests for DevDoc class"""

    def test_devdoc_basic_fields(self) -> None:
        """Test DevDoc parses basic fields"""
        devdoc_data = {
            "author": "Contract Author",
            "title": "Test Contract",
            "details": "Contract details",
            "methods": {},
        }
        devdoc = DevDoc(devdoc_data)
        assert devdoc.author == "Contract Author"
        assert devdoc.title == "Test Contract"
        assert devdoc.details == "Contract details"

    def test_devdoc_custom_fields_parsing(self) -> None:
        """Test DevDoc extracts contract-level custom fields"""
        devdoc_data = {
            "title": "Test Contract",
            "custom:security-contact": "security@example.com",
            "custom:oz-upgrades-unsafe-allow": "constructor",
            "methods": {},
        }
        devdoc = DevDoc(devdoc_data)
        assert devdoc.custom == {
            "custom:security-contact": "security@example.com",
            "custom:oz-upgrades-unsafe-allow": "constructor",
        }

    def test_devdoc_no_custom_fields(self) -> None:
        """Test DevDoc returns empty dict when no custom fields"""
        devdoc_data = {
            "title": "Test Contract",
            "author": "Author",
            "methods": {},
        }
        devdoc = DevDoc(devdoc_data)
        assert devdoc.custom == {}

    def test_devdoc_export_includes_custom(self) -> None:
        """Test DevDoc export includes custom fields"""
        devdoc_data = {
            "title": "Test Contract",
            "author": "Author",
            "details": "Details",
            "custom:security-contact": "security@example.com",
            "custom:license": "MIT",
            "methods": {},
        }
        devdoc = DevDoc(devdoc_data)
        exported = devdoc.export()

        assert exported["title"] == "Test Contract"
        assert exported["author"] == "Author"
        assert exported["details"] == "Details"
        assert exported["custom:security-contact"] == "security@example.com"
        assert exported["custom:license"] == "MIT"

    def test_devdoc_methods_have_custom(self) -> None:
        """Test DevDoc methods contain custom fields"""
        devdoc_data = {
            "title": "Test Contract",
            "custom:security-contact": "security@example.com",
            "methods": {
                "transfer(address,uint256)": {
                    "params": {"to": "recipient", "amount": "amount to transfer"},
                    "custom:security": "critical",
                    "custom:access": "onlyOwner",
                },
                "balanceOf(address)": {
                    "params": {"account": "address to check"},
                },
            },
        }
        devdoc = DevDoc(devdoc_data)

        # Contract-level custom
        assert devdoc.custom["custom:security-contact"] == "security@example.com"

        # Method with custom fields
        transfer_method = devdoc.methods["transfer(address,uint256)"]
        assert transfer_method.custom == {
            "custom:security": "critical",
            "custom:access": "onlyOwner",
        }

        # Method without custom fields
        balance_method = devdoc.methods["balanceOf(address)"]
        assert balance_method.custom == {}

    def test_devdoc_export_with_methods_custom(self) -> None:
        """Test DevDoc export includes method custom fields"""
        devdoc_data = {
            "title": "Test",
            "methods": {
                "foo()": {
                    "details": "foo details",
                    "custom:audit": "verified",
                },
            },
        }
        devdoc = DevDoc(devdoc_data)
        exported = devdoc.export()

        assert exported["methods"]["foo()"]["custom:audit"] == "verified"
        assert exported["methods"]["foo()"]["details"] == "foo details"


class TestNatspec:
    """Tests for Natspec class"""

    def test_natspec_basic(self) -> None:
        """Test Natspec combines user and dev docs"""
        userdoc = {"notice": "User notice", "methods": {}}
        devdoc = {"title": "Dev title", "methods": {}}
        natspec = Natspec(userdoc, devdoc)

        assert natspec.userdoc.notice == "User notice"
        assert natspec.devdoc.title == "Dev title"

    def test_natspec_with_custom_fields(self) -> None:
        """Test Natspec with custom fields in devdoc"""
        userdoc = {"notice": "Contract notice", "methods": {}}
        devdoc = {
            "title": "Test Contract",
            "custom:security-contact": "security@example.com",
            "custom:oz-upgrades": "safe",
            "methods": {
                "initialize()": {
                    "details": "Initializer function",
                    "custom:oz-upgrades-unsafe-allow": "constructor",
                },
            },
        }
        natspec = Natspec(userdoc, devdoc)

        # Contract-level custom
        assert natspec.devdoc.custom == {
            "custom:security-contact": "security@example.com",
            "custom:oz-upgrades": "safe",
        }

        # Method-level custom
        init_method = natspec.devdoc.methods["initialize()"]
        assert init_method.custom == {"custom:oz-upgrades-unsafe-allow": "constructor"}

    def test_natspec_real_world_example(self) -> None:
        """Test with realistic OpenZeppelin-style NatSpec"""
        userdoc = {
            "kind": "user",
            "methods": {
                "transfer(address,uint256)": {"notice": "Transfer tokens to recipient"},
            },
            "notice": "ERC20 Token",
            "version": 1,
        }
        devdoc = {
            "kind": "dev",
            "title": "ERC20 Token",
            "author": "OpenZeppelin",
            "custom:security-contact": "security@openzeppelin.com",
            "custom:oz-upgrades-unsafe-allow": "constructor delegatecall",
            "methods": {
                "transfer(address,uint256)": {
                    "params": {
                        "to": "The recipient address",
                        "amount": "The amount to transfer",
                    },
                    "return": "bool indicating success",
                    "custom:security": "reentrancy-safe",
                },
                "constructor": {
                    "custom:oz-upgrades-unsafe-allow": "constructor",
                },
            },
            "version": 1,
        }
        natspec = Natspec(userdoc, devdoc)

        # Verify contract-level custom fields
        assert "custom:security-contact" in natspec.devdoc.custom
        assert natspec.devdoc.custom["custom:security-contact"] == "security@openzeppelin.com"
        assert (
            natspec.devdoc.custom["custom:oz-upgrades-unsafe-allow"] == "constructor delegatecall"
        )

        # Verify method-level custom fields
        transfer = natspec.devdoc.methods["transfer(address,uint256)"]
        assert transfer.custom["custom:security"] == "reentrancy-safe"

        constructor = natspec.devdoc.methods["constructor"]
        assert constructor.custom["custom:oz-upgrades-unsafe-allow"] == "constructor"

        # Verify export roundtrip preserves custom fields
        exported = natspec.devdoc.export()
        assert exported["custom:security-contact"] == "security@openzeppelin.com"
        assert (
            exported["methods"]["transfer(address,uint256)"]["custom:security"] == "reentrancy-safe"
        )
