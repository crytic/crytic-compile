{ pkgs ? import <nixpkgs> {} }:
pkgs.python39Packages.buildPythonPackage rec {
  pname = "mypy";
  version = "0.942";
  src = pkgs.python39Packages.fetchPypi {
    inherit pname version;
    sha256 = "sha256-F+RGSf7JLp+CECtIo797SlUQrQzSL6IaEEgmtdtJA+I=";
  };
  doCheck = false;
  propagatedBuildInputs = with pkgs.python39Packages; [
    mypy-extensions
    tomli
    types-setuptools
    typing-extensions
  ];
}
