{
  description = "Cross-platform smart-contract compiler";

  # Flake inputs
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs";
    flake-utils.url = "github:numtide/flake-utils";
  };

  # Flake outputs
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        version = "0.2.5";
      in
      rec {

        # Provide packages for selected system types.
        packages = {

          default = packages.crytic-compile;

          crytic-compile = pkgs.callPackage pkgs.python38Packages.buildPythonPackage rec {
            pname = "crytic-compile";
            inherit version;
            format = "pyproject";
            src = ./.;
            propagatedBuildInputs = with pkgs.python38Packages; [
              cbor2
              pycryptodome
              setuptools
              wheel
            ];
            pythonRelaxDeps = true;
            doCheck = false;
          };

          # Custom derivations to set linters to specific versions
          black = pkgs.callPackage pkgs.python38Packages.buildPythonPackage rec {
            pname = "black";
            version = "22.3.0";
            src = pkgs.python38Packages.fetchPypi {
              inherit pname version;
              sha256 = "sha256-NQILiIbAIs7ZKCtRtah1ttGrDDh7MaBluE23wzCFynk=";
            };
            doCheck = false;
            propagatedBuildInputs = with pkgs.python38Packages; [
              click
              mypy-extensions
              pathspec
              platformdirs
              setuptools_scm
              tomli
              typing-extensions
            ];
          };

          darglint = pkgs.callPackage pkgs.python38Packages.buildPythonPackage rec {
            pname = "darglint";
            version = "1.8.0";
            src = pkgs.python38Packages.fetchPypi {
              inherit pname version;
              sha256 = "sha256-qmBe9HgXptFHl9MrOQRm7atiF2jqTKXMDzxU9tjcrsg=";
            };
            doCheck = false;
          };

          mypy = pkgs.python39.withPackages(ps: with ps; [
            types-setuptools
            setuptools
            (pkgs.python39Packages.buildPythonPackage rec {
              pname = "mypy";
              version = "0.942";
              src = pkgs.python39Packages.fetchPypi {
                inherit pname version;
                sha256 = "sha256-F+RGSf7JLp+CECtIo797SlUQrQzSL6IaEEgmtdtJA+I=";
              };
              doCheck = false;
              propagatedBuildInputs = with pkgs.python39Packages; [
                mypy-extensions
                tomli
                typing-extensions
              ];
            })
          ]);

          pylint = pkgs.callPackage pkgs.python39Packages.buildPythonPackage rec {
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
              (pkgs.python39Packages.buildPythonPackage rec {
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
              })
            ];
          };

        };

        apps = {
          default = {
            type = "app";
            program = "${self.packages.${system}.crytic-compile}/bin/crytic-compile";
          };
        };

        # Development environment output
        devShells = {
          default = pkgs.mkShell {
            # The Nix packages provided in the environment
            src = ./crytic_compile;
            packages = with pkgs; [
              packages.black
              packages.darglint
              packages.mypy
              packages.pylint
              # not-reloadable version of crytic-compile (not ideal!)
              packages.crytic-compile
              # # hot-reloadable version of crytic-compile (hopefully!)
              # # currently broken bc crytic_compile/platform clobbers the platform module of the std lib
              # (pkgs.python38Packages.buildPythonPackage rec {
              #   name = "crytic-compile";
              #   src = ./crytic_compile;
              #   propagatedBuildInputs = with pkgs.python38Packages; [
              #     cbor2
              #     pycryptodome
              #     setuptools
              #   ];
              # })
              python38
              virtualenv
              python38Packages.pip
              python38Packages.pycryptodome
              python38Packages.setuptools
            ];
          };
        };

      });
  }
