#!/bin/sh

# This script installs the Nix package manager on your system by
# downloading a binary distribution and running its installer script
# (which in turn creates and populates /nix).

{ # Prevent execution if this script was only partially downloaded
oops() {
    echo "$0:" "$@" >&2
    exit 1
}

umask 0022

tmpDir="$(mktemp -d -t nix-binary-tarball-unpack.XXXXXXXXXX || \
          oops "Can't create temporary directory for downloading the Nix binary tarball")"
cleanup() {
    rm -rf "$tmpDir"
}
trap cleanup EXIT INT QUIT TERM

require_util() {
    command -v "$1" > /dev/null 2>&1 ||
        oops "you do not have '$1' installed, which I need to $2"
}

case "$(uname -s).$(uname -m)" in
    Linux.x86_64) system=x86_64-linux; hash=49763fd7fa06bcb712ced2f3f11afd275e3a4d7bc5ff0d6fd1d50a4c3ce7bbf4;;
    Linux.i?86) system=i686-linux; hash=c87c376c2d5277d56664855c668a5dca957c51d1c654849571d12a1b90fbe75a;;
    Linux.aarch64) system=aarch64-linux; hash=733a26911193fdd44d5d68342075af5924d8c0701aae877e51a38d74ee9f4ff8;;
    Darwin.x86_64) system=x86_64-darwin; hash=f0f081331b79ce42a638e523c7c0e40ee1aa44641131a7da042230e3a7a2da04;;
    # eventually maybe: system=arm64-darwin; hash=@binaryTarball_arm64-darwin@;;
    Darwin.arm64) system=x86_64-darwin; hash=f0f081331b79ce42a638e523c7c0e40ee1aa44641131a7da042230e3a7a2da04;;
    *) oops "sorry, there is no binary distribution of Nix for your platform";;
esac

url="https://releases.nixos.org/nix/nix-2.3.9/nix-2.3.9-$system.tar.xz"

tarball="$tmpDir/$(basename "$tmpDir/nix-2.3.9-$system.tar.xz")"

require_util curl "download the binary tarball"
require_util tar "unpack the binary tarball"
if [ "$(uname -s)" != "Darwin" ]; then
    require_util xz "unpack the binary tarball"
fi

echo "downloading Nix 2.3.9 binary tarball for $system from '$url' to '$tmpDir'..."
curl -L "$url" -o "$tarball" || oops "failed to download '$url'"

if command -v sha256sum > /dev/null 2>&1; then
    hash2="$(sha256sum -b "$tarball" | cut -c1-64)"
elif command -v shasum > /dev/null 2>&1; then
    hash2="$(shasum -a 256 -b "$tarball" | cut -c1-64)"
elif command -v openssl > /dev/null 2>&1; then
    hash2="$(openssl dgst -r -sha256 "$tarball" | cut -c1-64)"
else
    oops "cannot verify the SHA-256 hash of '$url'; you need one of 'shasum', 'sha256sum', or 'openssl'"
fi

if [ "$hash" != "$hash2" ]; then
    oops "SHA-256 hash mismatch in '$url'; expected $hash, got $hash2"
fi

unpack=$tmpDir/unpack
mkdir -p "$unpack"
tar -xJf "$tarball" -C "$unpack" || oops "failed to unpack '$url'"

script=$(echo "$unpack"/*/install)

[ -e "$script" ] || oops "installation script is missing from the binary tarball!"
"$script" "$@"

} # End of wrapping
