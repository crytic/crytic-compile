"""Tests for Sourcify platform integration."""

import pytest

from crytic_compile import CryticCompile


@pytest.mark.slow
class TestSourcifyProxy:
    """Test proxy resolution via Sourcify."""

    # Diamond proxy on Arbitrum One with multiple facets
    TARGET = "sourcify-42161:0xD1A0060ba708BC4BCD3DA6C37EFa8deDF015FB70"
    EXPECTED_FACETS = 31

    def test_diamond_proxy_has_implementation_addresses(self) -> None:
        """Diamond proxy should populate implementation_addresses with facets."""
        cc = CryticCompile(self.TARGET)

        assert len(cc.compilation_units) == 1
        cu = next(iter(cc.compilation_units.values()))

        assert len(cu.implementation_addresses) == self.EXPECTED_FACETS

    def test_implementation_addresses_format(self) -> None:
        """Implementation addresses should be formatted as sourcify targets."""
        cc = CryticCompile(self.TARGET)
        cu = next(iter(cc.compilation_units.values()))

        for addr in cu.implementation_addresses:
            assert addr.startswith("sourcify-42161:0x"), f"Invalid format: {addr}"
            # Should be checksummed (mixed case)
            address_part = addr.split(":")[1]
            assert address_part != address_part.lower(), "Address should be checksummed"
