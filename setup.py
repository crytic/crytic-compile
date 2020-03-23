"""
CryticCompile package installation
"""
from setuptools import setup, find_packages

setup(
    name="crytic-compile",
    description="Util to facilitate smart contracts compilation.",
    url="https://github.com/crytic/crytic-compile",
    author="Trail of Bits",
    version="0.1.7",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=["pysha3>=1.0.2"],
    license="AGPL-3.0",
    long_description=open("README.md", encoding="utf8").read(),
    entry_points={"console_scripts": ["crytic-compile = crytic_compile.__main__:main"]},
)
