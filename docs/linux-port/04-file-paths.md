# Phase 4: File Paths

## Goal
Replace macOS-specific file paths with XDG Base Directory Specification paths for Linux.

## Current State
Multiple files use `~/Library/Application Support/dw1-silicon/`:

- `crates/dw1/src/main.rs` line 139-142: Save directory
- `crates/dw1/src/settings.rs` line 2: Settings file
- `crates/dw1/src/window/snapshot.rs` line 2: Reports directory
- `crates/dw1/src/main.rs` line 217: DuckStation card import

## XDG Base Directory Specification

The XDG spec defines standard locations for user files:

- **XDG_DATA_HOME**: `~/.local/share` (user data files)
- **XDG_CONFIG_HOME**: `~/.config` (config files)
- **XDG_CACHE_HOME**: `~/.cache` (cache files)

Fallbacks if environment variables not set:
- `XDG_DATA_HOME` → `~/.local/share`
- `XDG_CONFIG_HOME` → `~/.config`
- `XDG_CACHE_HOME` → `~/.cache`

## Changes Required

### 1. Save Directory

**File:** `crates/dw1/src/main.rs`

Replace `default_save_dir()` function (lines 139-143):

```rust
/// Default save directory by platform:
/// - macOS: `~/Library/Application Support/dw1-silicon`
/// - Linux: `$XDG_DATA_HOME/dw1-silicon` (default: `~/.local/share/dw1-silicon`)
pub fn default_save_dir() -> Option<std::path::PathBuf> {
    #[cfg(target_os = "macos")]
    {
        std::env::var_os("HOME").map(|h| {
            std::path::PathBuf::from(h).join("Library/Application Support/dw1-silicon")
        })
    }

    #[cfg(not(target_os = "macos"))]
    {
        let base = std::env::var_os("XDG_DATA_HOME")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| {
                let home = std::env::var_os("HOME")?;
                std::path::PathBuf::from(home).join(".local/share")
            });
        Some(base.join("dw1-silicon"))
    }
}
```

### 2. DuckStation Card Path

**File:** `crates/dw1/src/main.rs`

Replace `duckstation_card()` function (lines 214-219):

```rust
/// DuckStation memory card path by platform:
/// - macOS: `~/Library/Application Support/DuckStation/memcards/Digimon World (USA)_1.mcd`
/// - Linux: `$XDG_DATA_HOME/duckstation/memcards/Digimon World (USA)_1.mcd`
fn duckstation_card() -> Option<std::path::PathBuf> {
    #[cfg(target_os = "macos")]
    {
        let home = std::env::var_os("HOME")?;
        let card = std::path::PathBuf::from(home)
            .join("Library/Application Support/DuckStation/memcards/Digimon World (USA)_1.mcd");
        card.exists().then_some(card)
    }

    #[cfg(not(target_os = "macos"))]
    {
        let base = std::env::var_os("XDG_DATA_HOME")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| {
                let home = std::env::var_os("HOME")?;
                std::path::PathBuf::from(home).join(".local/share")
            });
        let card = base.join("duckstation/memcards/Digimon World (USA)_1.mcd");
        card.exists().then_some(card)
    }
}
```

### 3. Settings File

**File:** `crates/dw1/src/settings.rs`

Update module comment (line 1-2):

```rust
//! The window build's picture settings (Phase 8.4), kept in:
//! - macOS: `~/Library/Application Support/dw1-silicon/settings.txt`
//! - Linux: `$XDG_CONFIG_HOME/dw1-silicon/settings.txt` (default: `~/.config/dw1-silicon/settings.txt`)
```

Add helper function:

```rust
/// Default settings directory by platform.
fn default_settings_dir() -> std::path::PathBuf {
    #[cfg(target_os = "macos")]
    {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        std::path::PathBuf::from(home).join("Library/Application Support/dw1-silicon")
    }

    #[cfg(not(target_os = "macos"))]
    {
        let base = std::env::var("XDG_CONFIG_HOME")
            .unwrap_or_else(|_| {
                let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
                format!("{}/.config", home)
            });
        std::path::PathBuf::from(base).join("dw1-silicon")
    }
}
```

Update the settings path usage (find where settings.txt is read/written):

```rust
// Find the line that constructs the settings path and replace:
let settings_path = default_settings_dir().join("settings.txt");
```

### 4. Reports Directory

**File:** `crates/dw1/src/window/snapshot.rs`

Update module comment (line 1-2):

```rust
//! F12: a bug snapshot (Phase 9.3). Everything needed to look into a bug found in play goes into:
//! - macOS: `~/Library/Application Support/dw1-silicon/reports/<UTC time>/`
//! - Linux: `$XDG_DATA_HOME/dw1-silicon/reports/<UTC time>/` (default: `~/.local/share/dw1-silicon/reports/`)
```

Add helper function:

```rust
/// Default reports directory by platform.
fn default_reports_dir() -> std::path::PathBuf {
    #[cfg(target_os = "macos")]
    {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        std::path::PathBuf::from(home).join("Library/Application Support/dw1-silicon/reports")
    }

    #[cfg(not(target_os = "macos"))]
    {
        let base = std::env::var_os("XDG_DATA_HOME")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| {
                let home = std::env::var_os("HOME")?;
                std::path::PathBuf::from(home).join(".local/share")
            });
        base.join("dw1-silicon/reports")
    }
}
```

Update reports path usage (find where reports directory is created):

```rust
// Find the line that constructs the reports path and replace:
let reports_dir = default_reports_dir();
let report_dir = reports_dir.join(utc_timestamp);
```

### 5. Environment Variable Override

Add support for `DW1_DATA_DIR` and `DW1_CONFIG_DIR` to override defaults:

**File:** `crates/dw1/src/main.rs`

```rust
/// Save directory: `DW1_DATA_DIR`, else platform default, else None.
pub(crate) fn save_dir() -> Option<std::path::PathBuf> {
    match std::env::var_os("DW1_DATA_DIR") {
        Some(d) if d.is_empty() => None,
        Some(d) => Some(d.into()),
        None => default_save_dir(),
    }
}
```

Similarly for settings in `settings.rs`:

```rust
/// Settings directory: `DW1_CONFIG_DIR`, else platform default.
fn settings_dir() -> std::path::PathBuf {
    if let Ok(dir) = std::env::var("DW1_CONFIG_DIR") {
        return std::path::PathBuf::from(dir);
    }
    default_settings_dir()
}
```

### 6. Directory Creation

Ensure directories are created before use. Add to each function:

```rust
// In default_save_dir or when using it:
std::fs::create_dir_all(&dir).ok();
```

## Testing

### Test Paths are Correct

```bash
# On Linux
export DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue
export DW1_DATA_DIR=/tmp/test-dw1-data
./target/release/dw1

# Check directories were created
ls -la /tmp/test-dw1-data/dw1-silicon/
```

### Test Migration from macOS

If migrating from macOS build, copy saves:

```bash
# From macOS backup
cp -r ~/Library/Application\ Support/dw1-silicon/* ~/.local/share/dw1-silicon/
```

## Deliverables

- [x] Save directory uses XDG paths on Linux
- [x] Settings directory uses XDG paths on Linux
- [x] Reports directory uses XDG paths on Linux
- [x] DuckStation card path uses XDG paths on Linux
- [x] Environment variable overrides supported
- [x] Directories created automatically
- [ ] Saves work correctly on Linux
- [ ] Settings persist on Linux

## Debugging

### Check what path is being used

Add debug output:

```rust
eprintln!("dw1: save directory: {:?}", save_dir());
eprintln!("dw1: settings directory: {:?}", settings_dir());
```

### Check directory permissions

```bash
# Ensure user has write permissions
ls -ld ~/.local/share/dw1-silicon
```

### Test with custom directory

```bash
export DW1_DATA_DIR=/tmp/dw1-test
export DW1_CONFIG_DIR=/tmp/dw1-config
./target/release/dw1
```

## Commit Message

```
fs: use XDG paths on Linux for saves and settings

Replace macOS-specific ~/Library/Application Support paths with
XDG Base Directory Specification paths on Linux:

- Saves: $XDG_DATA_HOME/dw1-silicon (default: ~/.local/share/dw1-silicon)
- Settings: $XDG_CONFIG_HOME/dw1-silicon (default: ~/.config/dw1-silicon)
- Reports: $XDG_DATA_HOME/dw1-silicon/reports

Add DW1_DATA_DIR and DW1_CONFIG_DIR environment variables to override
defaults.

macOS paths remain unchanged for compatibility.
```

## Notes

### Why XDG?

XDG is the Linux standard for application file locations. Using it ensures:
- Consistency with other Linux applications
- Proper separation of data, config, and cache
- Respect for user expectations
- Easy backup/migration

### Migration

Users migrating from macOS can manually copy their saves to the new location.
Consider adding a migration utility in a future phase.

### Environment Variables

The override variables are useful for:
- Testing with different directories
- Portable installations
- Multiple configurations

### Next Steps

After this phase, move to **Phase 5: Crash Handler** to implement Linux signal
handling for crash traces.
