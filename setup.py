"""
CryticCompile package installation
"""
from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf8") as f:
    long_description = f.read()

setup(
    name="crytic-compile",
    description="Util to facilitate smart contracts compilation.",
    url="https://github.com/crytic/crytic-compile",
    author="Trail of Bits",
    version="0.3.0",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=["pycryptodome>=3.4.6", "cbor2"],
    license="AGPL-3.0",
    long_description=long_description,
    package_data={"crytic_compile": ["py.typed"]},
    entry_points={"console_scripts": ["crytic-compile = crytic_compile.__main__:main"]},
)
