{ pkgs ? import <nixpkgs> {} }:
pkgs.callPackage ./crytic-compile.nix {}
