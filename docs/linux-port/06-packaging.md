# Phase 6: Packaging

## Goal
Create Linux desktop integration (.desktop file, icon, installation documentation).

## Current State
- macOS uses .app bundle with Info.plist
- Packaging only exists for macOS

## Changes Required

### 1. Create .desktop File

**File:** `packaging/dw1-silicon.desktop`

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Digimon World
Comment=Native port of Digimon World (PS1)
Comment[es]=Port nativo de Digimon World (PS1)
Exec=/usr/local/bin/dw1
Icon=dw1-silicon
Terminal=false
Categories=Game;RolePlaying;
Keywords=Digimon;PS1;PlayStation;
StartupNotify=false
```

### 2. Install Script

**File:** `tools/install-linux.sh`

```bash
#!/bin/sh
# Installs dw1-silicon on Linux (requires sudo).
# Copies binary to /usr/local/bin, .desktop file to /usr/share/applications,
# and icon to /usr/share/icons/hicolor/256x256/apps.
set -eu

cd "$(dirname "$0")/.." || exit 1

if [ "$(id -u)" -ne 0 ]; then
    echo "install-linux.sh requires root (sudo). Run with:" >&2
    echo "  sudo ./tools/install-linux.sh" >&2
    exit 1
fi

BIN=target/release/dw1
if [ ! -x "$BIN" ]; then
    echo "dw1 binary not found at $BIN" >&2
    echo "Run ./tools/build-linux.sh first" >&2
    exit 1
fi

# Install binary
echo "Installing binary to /usr/local/bin/dw1..."
install -m 755 "$BIN" /usr/local/bin/dw1

# Install .desktop file
echo "Installing .desktop file to /usr/share/applications..."
install -m 644 packaging/dw1-silicon.desktop /usr/share/applications/

# Install icon
echo "Installing icon to /usr/share/icons/hicolor/256x256/apps..."
mkdir -p /usr/share/icons/hicolor/256x256/apps
install -m 644 packaging/icon-1024.png /usr/share/icons/hicolor/256x256/apps/dw1-silicon.png

# Update desktop database
echo "Updating desktop database..."
update-desktop-database /usr/share/applications || true
gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true

echo "Installation complete!"
echo "Run 'dw1' from the terminal or find it in your application menu."
echo ""
echo "Set your disc image with:"
echo "  export DW1_DISC=/path/to/Digimon\\ World\\ \\(USA\\).cue"
echo ""
echo "Or create a launcher script:"
echo "  echo '#!/bin/sh' > /usr/local/bin/dw1-launcher"
echo "  echo 'export DW1_DISC=/path/to/Digimon\\ World\\ \\(USA\\).cue' >> /usr/local/bin/dw1-launcher"
echo "  echo 'exec /usr/local/bin/dw1' >> /usr/local/bin/dw1-launcher"
echo "  chmod +x /usr/local/bin/dw1-launcher"
```

**Make executable:**
```bash
chmod +x tools/install-linux.sh
```

### 3. Uninstall Script

**File:** `tools/uninstall-linux.sh`

```bash
#!/bin/sh
# Uninstalls dw1-silicon from Linux (requires sudo).
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "uninstall-linux.sh requires root (sudo). Run with:" >&2
    echo "  sudo ./tools/uninstall-linux.sh" >&2
    exit 1
fi

echo "Removing dw1-silicon..."
rm -f /usr/local/bin/dw1
rm -f /usr/local/bin/dw1-launcher
rm -f /usr/share/applications/dw1-silicon.desktop
rm -f /usr/share/icons/hicolor/256x256/apps/dw1-silicon.png

# Update desktop database
echo "Updating desktop database..."
update-desktop-database /usr/share/applications || true
gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true

echo "Uninstallation complete!"
echo "Note: User data in ~/.local/share/dw1-silicon and ~/.config/dw1-silicon is preserved."
```

**Make executable:**
```bash
chmod +x tools/uninstall-linux.sh
```

### 4. Icon Sizes

Linux desktop environments expect icons at multiple sizes. Create symlinks or copies:

```bash
# In install-linux.sh, after installing the 256x256 icon:
for size in 16 32 48 64 128 256; do
    mkdir -p "/usr/share/icons/hicolor/${size}x${size}/apps"
    if [ "$size" -eq 256 ]; then
        install -m 644 packaging/icon-1024.png "/usr/share/icons/hicolor/${size}x${size}/apps/dw1-silicon.png"
    else
        # Use the same icon for all sizes (simple approach)
        ln -sf /usr/share/icons/hicolor/256x256/apps/dw1-silicon.png \
               "/usr/share/icons/hicolor/${size}x${size}/apps/dw1-silicon.png" || true
    fi
done
```

Or better, generate scaled versions with ImageMagick:

```bash
# In install-linux.sh:
if command -v convert > /dev/null 2>&1; then
    for size in 16 32 48 64 128; do
        mkdir -p "/usr/share/icons/hicolor/${size}x${size}/apps"
        convert packaging/icon-1024.png -resize "${size}x${size}" \
                "/usr/share/icons/hicolor/${size}x${size}/apps/dw1-silicon.png"
    done
fi
```

### 5. AppImage Support (Optional)

**File:** `tools/build-appimage.sh`

```bash
#!/bin/sh
# Builds an AppImage for dw1-silicon.
set -eu

cd "$(dirname "$0")/.." || exit 1

# Build the binary
./tools/build-linux.sh

# Create AppImage directory
APPDIR=build/dw1-silicon.AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# Copy files
cp target/release/dw1 "$APPDIR/usr/bin/"
cp packaging/dw1-silicon.desktop "$APPDIR/usr/share/applications/"
cp packaging/icon-1024.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/dw1-silicon.png"

# Download AppImage tool (appimagetool)
if [ ! -x build/appimagetool ]; then
    wget -O build/appimagetool https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x build/appimagetool
fi

# Build AppImage
build/appimagetool "$APPDIR" "build/dw1-silicon-$(git describe --tags --always).AppImage"

echo "AppImage built: build/dw1-silicon-$(git describe --tags --always).AppImage"
```

### 6. Flatpak Support (Optional)

**File:** `packaging/com.loafykitten.dw1-silicon.json`

```json
{
    "app-id": "com.loafykitten.dw1-silicon",
    "runtime": "org.freedesktop.Platform",
    "runtime-version": "23.08",
    "sdk": "org.freedesktop.Sdk",
    "command": "dw1",
    "finish-args": [
        "--share=ipc",
        "--socket=x11",
        "--device=dri",
        "--filesystem=home:ro"
    ],
    "modules": [
        {
            "name": "dw1-silicon",
            "buildsystem": "simple",
            "build-commands": [
                "cargo build --release",
                "install -D target/release/dw1 /app/bin/dw1",
                "install -D packaging/dw1-silicon.desktop /app/share/applications/com.loafykitten.dw1-silicon.desktop",
                "install -D packaging/icon-1024.png /app/share/icons/hicolor/256x256/apps/com.loafykitten.dw1-silicon.png"
            ],
            "sources": [
                {
                    "type": "dir",
                    "path": "."
                }
            ]
        }
    ]
}
```

Build:
```bash
flatpak-builder build/ packaging/com.loafykitten.dw1-silicon.json
```

### 7. Update README

Add to README.md:

```markdown
## Linux Installation

### From Source

```sh
git clone https://github.com/loafykitten/dw1-silicon.git
cd dw1-silicon
git submodule update --init decomp
git -C decomp submodule update --init external/psyq_headers
python3 -m venv .venv && .venv/bin/pip install pyyaml cmake
./tools/build-linux.sh
sudo ./tools/install-linux.sh
```

### Running

```sh
dw1
```

Set your disc image:
```sh
export DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue
dw1
```

### Uninstalling

```sh
sudo ./tools/uninstall-linux.sh
```

### AppImage (Portable)

Download or build the AppImage and run:
```sh
chmod +x dw1-silicon-*.AppImage
./dw1-silicon-*.AppImage
```
```

## Deliverables

- [x] .desktop file created
- [x] Install script created
- [x] Uninstall script created
- [x] Icon handling implemented
- [x] README updated with Linux instructions
- [ ] Installation tested
- [ ] Desktop menu entry works
- [ ] Icon displays correctly

## Testing

### Test Installation

```bash
sudo ./tools/install-linux.sh

# Check binary installed
which dw1

# Check .desktop file
cat /usr/share/applications/dw1-silicon.desktop

# Check icon
ls -l /usr/share/icons/hicolor/256x256/apps/dw1-silicon.png
```

### Test Desktop Entry

```bash
# Launch from desktop (if using GNOME/KDE)
# Should appear in application menu under Games

# Or launch directly
dw1
```

### Test Uninstallation

```bash
sudo ./tools/uninstall-linux.sh

# Verify files removed
! which dw1
! test -f /usr/share/applications/dw1-silicon.desktop
```

### Test AppImage (if built)

```bash
chmod +x build/dw1-silicon-*.AppImage
./build/dw1-silicon-*.AppImage
```

## Debugging

### If icon doesn't show

Update icon cache:
```bash
gtk-update-icon-cache -f -t /usr/share/icons/hicolor
```

### If desktop entry doesn't appear

Check .desktop file syntax:
```bash
desktop-file-validate /usr/share/applications/dw1-silicon.desktop
```

### If AppImage doesn't run

Check it's executable:
```bash
file build/dw1-silicon-*.AppImage
chmod +x build/dw1-silicon-*.AppImage
```

Run with FUSE debug:
```bash
./build/dw1-silicon-*.AppImage --appimage-extract
cd squashfs-root
./AppRun
```

## Commit Message

```
packaging: add Linux desktop integration

Add .desktop file, install/uninstall scripts, and icon handling for
Linux desktop integration.

The install script:
- Copies binary to /usr/local/bin
- Installs .desktop file to /usr/share/applications
- Installs icon to /usr/share/icons/hicolor
- Updates desktop database

User data remains in XDG directories (~/.local/share and ~/.config).

Add Linux installation instructions to README.md.

macOS .app packaging remains unchanged.
```

## Notes

### Why /usr/local/bin?

/usr/local/bin is standard for manually installed software and doesn't
require packaging system integration. For distro packages, use /usr/bin.

### Why not system packages?

Creating proper .deb/.rpm packages requires more work (maintainer info,
build scripts for each distro). AppImage or Flatpak are better for
portable distribution.

### Icon naming

Using `dw1-silicon` as the icon name avoids conflicts with other
Digimon-related applications.

### Next Steps

After this phase, move to **Phase 7: Testing** to verify the port works
correctly with the oracle.
