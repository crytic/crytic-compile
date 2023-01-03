let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix";
    ref = "refs/tags/3.5.0";
  }) {};
  pkgs = import <nixpkgs> {};
in
  mach-nix.buildPythonPackage rec {
    pname = "darglint";
    version = "1.8.0";
    src = pkgs.fetchFromGitHub {
      owner = "terrencepreilly";
      repo = "darglint";
      rev = "refs/tags/v${version}";
      hash = "sha256:u/U0Plk1QTqqSCuuXdcQhaGGxyscdUDYabUzjJeISlw=";
    };
  }
