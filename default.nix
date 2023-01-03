{ pkgs ? import <nixpkgs> {} }:
pkgs.callPackage ./nix/crytic-compile.nix {}
