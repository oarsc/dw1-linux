#!/bin/sh
# Builds and packages dw1 for Linux: a plain release binary plus a .desktop file
# and icon for desktop integration. Unlike the old macOS make-app.sh, this does
# not create an app bundle; Linux doesn't use those.
#
#   tools/make-linux.sh             build only
#   tools/make-linux.sh --install   also install to /usr/local (desktop file, icon)
#
# The package holds code and text built from the game, so it's for your own use:
# don't share it. You still need your own legal copy of the Digimon World disc.
set -eu
cd "$(dirname "$0")/.." || exit 1

install=0
case "${1:-}" in
    --install) install=1 ;;
    "") ;;
    *) echo "usage: tools/make-linux.sh [--install]" >&2; exit 2 ;;
esac

# CMake (SDL's build): the one on PATH, else the repo's .venv.
if ! command -v cmake > /dev/null 2>&1 && [ -x .venv/bin/cmake ]; then
    CMAKE="$PWD/.venv/bin/cmake"
    export CMAKE
fi
cargo build --release -p dw1

bin=target/release/dw1
version=$(sed -n 's/^version = "\(.*\)"/\1/p' crates/dw1/Cargo.toml | head -n 1)

# Sanity: the binary should be a native Linux ELF.
file="$bin"
if ! file "$file" | grep -q 'ELF'; then
    echo "make-linux: $file is not a Linux ELF executable" >&2
    exit 1
fi

echo "make-linux: built $bin ($version)"

if [ "$install" = 1 ]; then
    prefix="${PREFIX:-/usr/local}"

    # Install the binary.
    mkdir -p "$prefix/bin"
    cp "$bin" "$prefix/bin/dw1"
    chmod 755 "$prefix/bin/dw1"

    # Install the .desktop file.
    sed -e "s|@VERSION@|$version|g" packaging/dw1.desktop.in > /tmp/dw1.desktop
    mkdir -p "$prefix/share/applications"
    cp /tmp/dw1.desktop "$prefix/share/applications/dw1.desktop"
    chmod 644 "$prefix/share/applications/dw1.desktop"

    # Install the icon (1024x1024 PNG).
    mkdir -p "$prefix/share/icons/hicolor/1024x1024/apps"
    cp packaging/icon-1024.png "$prefix/share/icons/hicolor/1024x1024/apps/dw1.png"
    chmod 644 "$prefix/share/icons/hicolor/1024x1024/apps/dw1.png"

    # Update the desktop icon cache if available.
    if command -v gtk-update-icon-cache > /dev/null 2>&1; then
        gtk-update-icon-cache -q "$prefix/share/icons/hicolor" 2>/dev/null || true
    fi
    if command -v update-desktop-database > /dev/null 2>&1; then
        update-desktop-database "$prefix/share/applications" 2>/dev/null || true
    fi

    echo "make-linux: installed to $prefix (bin, .desktop, icon)"
fi
