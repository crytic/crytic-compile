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

let
  pkgs = import (
    # commit hash from: https://lazamar.co.uk/nix-versions/?channel=nixpkgs-unstable&package=mypy
    fetchTarball "https://github.com/NixOS/nixpkgs/archive/bf972dc380f36a3bf83db052380e55f0eaa7dcb6.tar.gz"
    # fetchTarball "https://github.com/NixOS/nixpkgs/archive/ff8b619cfecb98bb94ae49ca7ceca937923a75fa.tar.gz"
  ) {};
  mypy = pkgs.python3Packages.mypy.overrideAttrs (_: rec {
    version = "2.13.4";
    src = pkgs.fetchFromGitHub {
      owner = "python";
      repo = "mypy";
      rev = "refs/tags/v${version}";
      hash = "sha256-CMbw6D6szQvur+13halZrskSV/9rDaThMGLeGxfjqWo=";
    };
    patches = [];
  });
in mypy
