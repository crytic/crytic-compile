let
  pkgs = import (
    # commit hash from: https://lazamar.co.uk/nix-versions/?channel=nixpkgs-unstable&package=pylint
    fetchTarball "https://github.com/NixOS/nixpkgs/archive/bf972dc380f36a3bf83db052380e55f0eaa7dcb6.tar.gz"
  ) {};
  pylint = pkgs.python3Packages.pylint.overrideAttrs (_: rec {
    version = "2.13.4";
    src = pkgs.fetchFromGitHub {
      owner = "PyCQA";
      repo = "pylint";
      rev = "refs/tags/v${version}";
      hash = "sha256-CMbw6D6szQvur+13halZrskSV/9rDaThMGLeGxfjqWo=";
    };
  });
in pylint
