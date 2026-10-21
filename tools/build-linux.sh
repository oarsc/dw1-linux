#!/bin/sh
# Builds dw1 for Linux (release build).
# On Linux, we don't create an app bundle - just the binary.
# This script is intended to run inside the Docker container via ./do.

set -eu

cd "$(dirname "$0")/.." || exit 1

# CMake (SDL's build): the one on PATH, else the repo's .venv
if ! command -v cmake > /dev/null 2>&1 && [ -x .venv/bin/cmake ]; then
    CMAKE="$PWD/.venv/bin/cmake"
    export CMAKE
fi

cargo build --release -p dw1

bin=target/release/dw1

echo "build-linux: built $bin"
echo "build-linux: run it (the disc in disc/ is found on its own): $bin"
