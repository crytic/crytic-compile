{ pkgs ? import <nixpkgs> {} }:

pkgs.python38Packages.buildPythonPackage rec {
  name = "crytic-compile";
  src = ./crytic_compile;
  propagatedBuildInputs = with pkgs.python38Packages; [ pycryptodome setuptools ];
}

# let
#   mach-nix = import (builtins.fetchGit {
#     url = "https://github.com/DavHau/mach-nix";
#     ref = "refs/tags/3.5.0";
#   }) {};
# in
#   mach-nix.mkPythonShell {
#     requirements = ''
#       pycryptodome
#       setuptools
#     '';
#   }

# pkgs.mkShell {
#   python = pkgs.python38.withPackages (ps: with ps; [
#     pip
#   ]);
#
#   shellHook = ''
#     echo hello crytic-compile shell
#   '';
#
#   packages = [
#
#     # (pkgs.python38Packages.buildPythonPackage rec {
#     #   name = "crytic-compile";
#     #   src = ./crytic_compile;
#     #   propagatedBuildInputs = with pkgs.python38Packages; [ pycryptodome setuptools ];
#     # })
#
#     # (pkgs.python38Packages.buildPythonPackage rec {
#     #   pname = "crytic-compile";
#     #   version = "0.2.5";
#     #   format = "setuptools";
#     #   src = ./.;
#     #   propagatedBuildInputs = with pkgs.python38Packages; [ pycryptodome setuptools ];
#     #   doCheck = false;
#     #   pythonRelaxDeps = true;
#     # })
#
#     (pkgs.python38.withPackages (ps: with ps; [ pip ]))
#     pkgs.black
#     pkgs.pylint
#     pkgs.solc-select
#   ];
# }
