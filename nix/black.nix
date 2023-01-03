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
    platformdirs
    typing-extensions
    click
    tomli
    mypy-extensions
    pathspec
  ];
}

# let
#   pkgs = import (
#     # commit hash from: https://lazamar.co.uk/nix-versions/?channel=nixpkgs-unstable&package=black
#     # fetchTarball "https://github.com/NixOS/nixpkgs/archive/ff8b619cfecb98bb94ae49ca7ceca937923a75fa.tar.gz"
#     fetchTarball "https://github.com/NixOS/nixpkgs/archive/bf972dc380f36a3bf83db052380e55f0eaa7dcb6.tar.gz"
#   ) {};
#   black = pkgs.python3Packages.black.overrideAttrs (_: rec {
#     version = "22.3.0";
#     src = pkgs.fetchFromGitHub {
#       owner = "psf";
#       repo = "black";
#       rev = "refs/tags/v${version}";
#       hash = "sha256-CMbw6D6szQvur+13halZrskSV/9rDaThMGLeGxfjqWo=";
#     };
#   });
# in black
