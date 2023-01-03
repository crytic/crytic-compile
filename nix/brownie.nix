let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix";
    ref = "refs/tags/3.5.0";
  }) {};
  pkgs = import <nixpkgs> {};
in
  mach-nix.buildPythonPackage rec {
    pname = "eth-brownie";
    version = "1.19.2";
    src = pkgs.fetchFromGitHub {
      owner = "eth-brownie";
      repo = "brownie";
      rev = "refs/tags/v${version}";
      hash = "sha256-nKBijlGznWMYpulz0RNZK2tevASzkeC5rEw6NvazSXI=";
    };
    providers = {
      _default = "nixpkgs,sdist,wheel";
      aiohttp = "nixpkgs,sdist,wheel,conda";
    };
  }
