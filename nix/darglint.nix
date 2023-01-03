{ pkgs ? import <nixpkgs> {} }:

pkgs.python38Packages.buildPythonPackage rec {
  pname = "darglint";
  version = "1.8.0";
  src = pkgs.python38Packages.fetchPypi {
    inherit pname version;
    sha256 = "sha256-qmBe9HgXptFHl9MrOQRm7atiF2jqTKXMDzxU9tjcrsg=";
  };
  doCheck = false;
}
