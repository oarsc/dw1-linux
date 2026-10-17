# Phase 3: Rendering Backend

## Goal
Switch from Metal (macOS) to Vulkan or OpenGL (Linux) for window rendering.

## Current State
- `crates/render/Cargo.toml` uses Metal feature: `features = ["metal", "wgsl", "std"]`
- Rendering code assumes Metal backend
- Window code references Metal specifically

## Changes Required

### 1. Update wgpu Features

**File:** `crates/render/Cargo.toml`

Change from:
```toml
wgpu = { version = "30.0.1", default-features = false, features = ["metal", "wgsl", "std"] }
```

To (Vulkan - recommended):
```toml
wgpu = { version = "30.0.1", default-features = false, features = ["vulkan", "wgsl", "std"] }
```

Or (OpenGL - alternative):
```toml
wgpu = { version = "30.0.1", default-features = false, features = ["gl", "wgsl", "std"] }
```

**Recommendation:** Use Vulkan for better performance and modern features.
OpenGL as fallback if Vulkan drivers are unavailable.

### 2. Conditional Features (Optional)

For supporting both platforms in the same Cargo.toml:

```toml
[target.'cfg(target_os = "macos")'.dependencies]
wgpu = { version = "30.0.1", default-features = false, features = ["metal", "wgsl", "std"] }

[target.'cfg(not(target_os = "macos"))'.dependencies]
wgpu = { version = "30.0.1", default-features = false, features = ["vulkan", "wgsl", "std"] }
```

This keeps Metal on macOS and uses Vulkan elsewhere.

### 3. Update Comments

**File:** `crates/render/src/lib.rs`

Line 1:
```rust
// From: The window's picture on wgpu (Metal): the game's display...
// To: The window's picture on wgpu (Vulkan/OpenGL on Linux, Metal on macOS): the game's display...
```

**File:** `crates/render/Cargo.toml`

Line 3:
```rust
// From: description = "Shows the game's picture in the window with wgpu on Metal"
// To: description = "Shows the game's picture in the window with wgpu (Vulkan/OpenGL on Linux, Metal on macOS)"
```

**File:** `crates/dw1/src/window.rs`

Line 1:
```rust
// From: The window host: the game's display shown through `render` (wgpu on Metal)...
// To: The window host: the game's display shown through `render` (wgpu on Vulkan/OpenGL on Linux, Metal on macOS)...
```

Line 201:
```rust
// From: Declared before `window`, so it goes first (it draws into the window's Metal layer).
// To: Declared before `window`, so it goes first (it draws into the window's surface).
```

Line 429:
```rust
// Find the line with .metal_view() and comment update:
// From: Uses Metal-specific method
// To: Uses wgpu surface (cross-platform)
```

Note: The actual `.metal_view()` call is likely in SDL3's Metal backend - this
may not need code changes if SDL3 handles it automatically.

### 4. No Code Changes Needed

The wgpu API is backend-agnostic. The rendering code in `crates/render/src/lib.rs`
should work unchanged - wgpu handles the differences between Metal, Vulkan, and
OpenGL internally.

### 5. Install Vulkan/OpenGL Dependencies

**For Vulkan (recommended):**

Debian/Ubuntu:
```bash
sudo apt install libvulkan-dev vulkan-tools
```

Fedora/RHEL:
```bash
sudo dnf install vulkan-devel
```

Arch:
```bash
sudo pacman -S vulkan-devel
```

**For OpenGL (alternative):**

Debian/Ubuntu:
```bash
sudo apt install libgl1-mesa-dev
```

Fedora/RHEL:
```bash
sudo dnf install mesa-libGL-devel
```

Arch:
```bash
sudo pacman -S mesa
```

### 6. Test Build

```bash
# Clean build to ensure features are picked up
cargo clean

# Build
cargo build --release -p dw1

# Should succeed now that Phases 1-3 are done
```

### 7. Test Window (Basic)

```bash
# Set up disc
export DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue

# Run
./target/release/dw1
```

Expected:
- Window opens
- Splash screen displays
- May fail on file paths (Phase 4) or crash handler (Phase 5)

If window opens and splash displays, Phase 3 is successful.

## Vulkan vs OpenGL

### Vulkan (Recommended)
**Pros:**
- Modern, low-overhead API
- Better performance
- Better supported on modern GPUs
- Future-proof

**Cons:**
- Requires Vulkan drivers
- Older GPUs may not support it
- Slightly more complex driver stack

### OpenGL (Alternative)
**Pros:**
- Ubiquitous support
- Works on older hardware
- Simpler driver stack

**Cons:**
- Older API
- May have performance limitations
- Less future-proof

**Recommendation:** Use Vulkan by default, with OpenGL as fallback if needed.

## Testing Vulkan Installation

```bash
# Test Vulkan is installed
vulkaninfo | head

# Should output driver information
```

If `vulkaninfo` is not found or fails, Vulkan is not properly installed.

## Debugging

### If wgpu fails to find Vulkan backend

Check wgpu is using the right backend:
```rust
// In crates/render/src/lib.rs, add debug output:
let adapter = pollster::block_on(instance.request_adapter(&RequestAdapterOptions {
    compatible_surface: Some(&surface),
    ..Default::default()
}))
.map_err(|e| {
    eprintln!("wgpu error requesting adapter: {}", e);
    e.to_string()
})?;
```

### If SDL3 doesn't find Vulkan

SDL3 may need to be built with Vulkan support. Check SDL3 version and build flags.

### If using OpenGL and it fails

Try Vulkan instead, or check Mesa drivers:
```bash
glxinfo | grep "OpenGL version"
```

## Deliverables

- [x] `crates/render/Cargo.toml` features updated (conditional or Vulkan)
- [x] Comments updated to reflect cross-platform support
- [x] Vulkan/OpenGL dependencies documented
- [ ] Full build succeeds
- [ ] Window opens and displays splash

## Testing

**Build test:**
```bash
cargo build --release -p dw1
test -x target/release/dw1
```

**Runtime test:**
```bash
export DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue
./target/release/dw1

# Check for window creation in logs
# Should see window open (even if it fails later)
```

**Vulkan test:**
```bash
vulkaninfo > /dev/null 2>&1 && echo "Vulkan OK" || echo "Vulkan missing"
```

## Commit Message

```
render: use Vulkan/OpenGL on Linux instead of Metal

Update crates/render/Cargo.toml to use Vulkan (or OpenGL) on Linux,
while keeping Metal on macOS via target-specific dependencies.

Update comments to reflect cross-platform rendering support.

The wgpu API is backend-agnostic, so no rendering code changes are needed.

With this, the window build should work on Linux (pending file path
changes in Phase 4).
```

## Notes

### Why conditional features?

This allows the same codebase to build on both platforms without
feature toggles. Cargo automatically selects the right feature based
on the target OS.

### SDL3 and Vulkan

SDL3's Metal backend uses `.metal_view()`, but for Vulkan/OpenGL it
uses different window system integration. This is handled internally
by SDL3 - the application code doesn't need to change.

### Performance

Vulkan should perform as well as or better than Metal on comparable
hardware. The actual performance depends on the GPU and drivers.

### Next Steps

After this phase, move to **Phase 4: File Paths** to fix save directory,
settings, and other file path issues.
