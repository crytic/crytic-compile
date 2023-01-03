{ pkgs ? import <nixpkgs> {} }:

let
  inherit (pkgs) python38Packages;
in
  python38Packages.buildPythonPackage rec {
    pname = "crytic-compile";
    version = "0.2.5";
    format = "pyproject";
    src = ../.;
    propagatedBuildInputs = with python38Packages; [
      cbor2
      pycryptodome
      setuptools
    ];
    pythonRelaxDeps = true;
    doCheck = false;
  }
