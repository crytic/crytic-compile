{ pkgs ? import <nixpkgs> {} }:

pkgs.python39Packages.buildPythonPackage rec {
  pname = "mypy";
  version = "0.942";
  src = pkgs.python39Packages.fetchPypi {
    inherit pname version;
    sha256 = "sha256-F+RGSf7JLp+CECtIo797SlUQrQzSL6IaEEgmtdtJA+I=";
  };
  doCheck = false;
  buildInputs = with pkgs.python39Packages; [ setuptools ];

  python = pkgs.python39.withPackages (ps: with ps; [
    types-setuptools
  ]);

  propagatedBuildInputs = with pkgs.python39Packages; [
    mypy-extensions
    tomli
    types-setuptools
    typing-extensions
    # (pkgs.python39Packages.buildPythonPackage rec {
    #   pname = "types-pkg-resources";
    #   version = "0.1.3";
    #   src = pkgs.python39Packages.fetchPypi {
    #     inherit pname version;
    #     sha256 = "sha256-NQILiIbAIs7ZKCtRtah1ttGrDDh7MaBluE23wzCFynk=";
    #   };
    #   doCheck = false;
    # })
  ];
}

# let
#   mach-nix = import (builtins.fetchGit {
#     url = "https://github.com/DavHau/mach-nix";
#     ref = "refs/tags/3.5.0";
#   }) {};
#   pkgs = import <nixpkgs> {};
# in
#   mach-nix.buildPythonPackage rec {
#     pname = "mypy";
#     version = "2.13.4";
#     src = pkgs.fetchFromGitHub {
#       owner = "python";
#       repo = "mypy";
#       rev = "refs/tags/v${version}";
#       hash = "sha256-CMbw6D6szQvur+13halZrskSV/9rDaThMGLeGxfjqWo=";
#     };
#     patches = [];
#     providers = {
#       _default = "nixpkgs,sdist,wheel";
#       astroid = "conda";
#     };
#   }

# let
#   pkgs = import (
#     # commit hash from: https://lazamar.co.uk/nix-versions/?channel=nixpkgs-unstable&package=mypy
#     fetchTarball "https://github.com/NixOS/nixpkgs/archive/bf972dc380f36a3bf83db052380e55f0eaa7dcb6.tar.gz"
#     # fetchTarball "https://github.com/NixOS/nixpkgs/archive/ff8b619cfecb98bb94ae49ca7ceca937923a75fa.tar.gz"
#   ) {};
#   mypy = pkgs.python3Packages.mypy.overrideAttrs (_: rec {
#     version = "2.13.4";
#     src = pkgs.fetchFromGitHub {
#       owner = "python";
#       repo = "mypy";
#       rev = "refs/tags/v${version}";
#       hash = "sha256-CMbw6D6szQvur+13halZrskSV/9rDaThMGLeGxfjqWo=";
#     };
#     patches = [];
#   });
# in mypy
