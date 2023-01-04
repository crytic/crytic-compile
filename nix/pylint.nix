{ pkgs ? import <nixpkgs> {} }:
let
  astroid = pkgs.python39Packages.buildPythonPackage rec {
    pname = "astroid";
    version = "2.11.7";
    src = pkgs.python39Packages.fetchPypi {
      inherit pname version;
      sha256 = "sha256-uyRhXHf0g3xwdmnRaQczE3SuipZGUKZpmdo/XKaNyUY=";
    };
    doCheck = false;
    propagatedBuildInputs = with pkgs.python39Packages; [
      lazy-object-proxy
      typing-extensions
      wrapt
    ];
  };
in
  pkgs.python39Packages.buildPythonPackage rec {
    pname = "pylint";
    version = "2.13.4";
    src = pkgs.python39Packages.fetchPypi {
      inherit pname version;
      sha256 = "sha256-fMbQxPYd/0QPnti2V/Ts1hXc/jU0WVPrex3HSv6QHXo=";
    };
    doCheck = false;
    propagatedBuildInputs = with pkgs.python39Packages; [
      isort
      tomli
      mccabe
      platformdirs
      dill
      astroid
    ];
  }
