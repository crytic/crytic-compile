{ pkgs ? import <nixpkgs> {} }:

pkgs.python38Packages.buildPythonPackage rec {
  pname = "black";
  version = "22.3.0";
  src = pkgs.python38Packages.fetchPypi {
    inherit pname version;
    sha256 = "sha256-NQILiIbAIs7ZKCtRtah1ttGrDDh7MaBluE23wzCFynk=";
  };
  doCheck = false;
  propagatedBuildInputs = with pkgs.python38Packages; [
    click
    mypy-extensions
    pathspec
    platformdirs
    setuptools_scm
    tomli
    typing-extensions
  ];
}
