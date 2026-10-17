# Phase 7: Testing

## Goal
Verify the Linux port works correctly by running oracle tests and comparing with macOS builds.

## Current State
- 43 certified replays exist in `tools/replay-check.sh`
- Oracle uses PCSX-Redux emulator as reference
- Replays check canonical state and frame-by-frame behavior

## Test Strategy

### 1. Headless Replays

First, test headless mode (no window) to verify core game logic:

```bash
# Set up disc
export DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue

# Run a simple replay
export DW1_REPLAY=oracle/replays/new-game.txt
export DW1_OUT=/tmp/dw1-test
./target/release/dw1

# Check output
ls -la /tmp/dw1-test/
```

### 2. Run All Certified Replays

Use the existing replay check script:

```bash
# Modify tools/replay-check.sh to use Linux binary
# Or run manually:

cd oracle
for replay in replays/*.txt; do
    echo "Testing $replay..."
    DW1_REPLAY="$replay" DW1_OUT="/tmp/dw1-test-$(basename $replay .txt)" \
        ../target/release/dw1
done
```

### 3. Compare with macOS

Run the same replays on macOS and compare outputs:

```bash
# On macOS
DW1_REPLAY=oracle/replays/new-game.txt DW1_OUT=/tmp/dw1-macos ./target/release/dw1

# On Linux
DW1_REPLAY=oracle/replays/new-game.txt DW1_OUT=/tmp/dw1-linux ./target/release/dw1

# Compare canonical state
tools/oracle/compare_canon.py /tmp/dw1-macos /tmp/dw1-linux
```

Expected: All checkpoints should be identical.

### 4. Window Mode Testing

Test the windowed build:

```bash
export DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue
./target/release/dw1
```

Check:
- [ ] Window opens
- [ ] Splash screen displays
- [ ] Game starts
- [ ] Controls work (keyboard/gamepad)
- [ ] Audio plays
- [ ] Picture displays correctly

### 5. Save System Testing

Test save/load functionality:

```bash
# Start a new game
# Save in-game
# Exit
# Restart
# Load save
# Verify state matches
```

Check saves are in XDG directory:
```bash
ls -la ~/.local/share/dw1-silicon/saves/
```

### 6. Settings Testing

Test settings persistence:

```bash
# Run game, change settings with F2-F5
# Exit
# Restart
# Verify settings persisted

cat ~/.config/dw1-silicon/settings.txt
```

### 7. Audio Testing

Test audio output:

```bash
# Ensure audio device is available
pactl list sinks  # PulseAudio
# or
aplay -l          # ALSA

# Run game
./target/release/dw1

# Check audio plays during gameplay
```

### 8. Gamepad Testing

Test gamepad support:

```bash
# Connect gamepad
ls /dev/input/js*  # Check gamepad is detected

# Run game
./target/release/dw1

# Test buttons work in-game
```

### 9. Crash Handler Testing

Test crash handler (if implemented):

```bash
export DW1_CRASH_TRACE=1
./target/release/dw1

# If a crash occurs, check backtrace is printed
```

### 10. Performance Testing

Compare performance with macOS:

```bash
# Time a replay on both platforms
time DW1_REPLAY=oracle/replays/new-game.txt ./target/release/dw1
```

Linux should be similar or better performance (same hardware).

## Test Checklist

### Core Functionality
- [ ] Binary builds without errors
- [ ] Binary runs without immediate crash
- [ ] Disc is detected and loaded
- [ ] Game boots to main menu
- [ ] New game starts
- [ ] In-game saves work
- [ ] Load game works

### Oracle Tests
- [ ] new-game replay passes
- [ ] file-city-walk replay passes
- [ ] care-fixture replay passes
- [ ] battle-fixture replay passes
- [ ] training-fixture replay passes
- [ ] All 43 certified replays pass

### Window Mode
- [ ] Window opens at correct size
- [ ] Splash screen displays
- [ ] Game picture displays
- [ ] F2-F5 hotkeys work
- [ ] F11 fullscreen works
- [ ] F12 snapshot works

### Input
- [ ] Keyboard controls work
- [ ] Gamepad is detected
- [ ] Gamepad buttons work
- [ ] D-pad/stick works

### Audio
- [ ] Audio device is detected
- [ ] Music plays
- [ ] Sound effects play
- [ ] Audio doesn't desync

### File System
- [ ] Saves go to XDG directory
- [ ] Settings go to XDG directory
- [ ] Reports go to XDG directory
- [ ] DuckStation card import works

### Desktop Integration
- [ ] .desktop file validates
- [ ] Icon displays in menu
- [ ] Application launches from menu
- [ ] Uninstall script works

## Regression Tests

Create a test script to run basic regression tests:

**File:** `tools/test-linux.sh`

```bash
#!/bin/sh
# Basic regression tests for Linux port
set -eu

cd "$(dirname "$0")/.." || exit 1

echo "=== dw1-silicon Linux Regression Tests ==="

# Check binary exists
if [ ! -x target/release/dw1 ]; then
    echo "FAIL: Binary not found. Run ./tools/build-linux.sh first"
    exit 1
fi
echo "✓ Binary exists"

# Check disc is set
if [ -z "$DW1_DISC" ]; then
    echo "FAIL: DW1_DISC not set"
    echo "Set with: export DW1_DISC=/path/to/Digimon\\ World\\ \\(USA\\).cue"
    exit 1
fi
echo "✓ DW1_DISC set"

# Test headless new-game
echo "Testing new-game replay..."
export DW1_REPLAY=oracle/replays/new-game.txt
export DW1_OUT=/tmp/dw1-test-newgame
if ./target/release/dw1 > /tmp/dw1-test-newgame.log 2>&1; then
    echo "✓ new-game replay completed"
else
    echo "FAIL: new-game replay failed"
    cat /tmp/dw1-test-newgame.log
    exit 1
fi

# Check output exists
if [ ! -d "$DW1_OUT" ]; then
    echo "FAIL: Output directory not created"
    exit 1
fi
echo "✓ Output directory created"

# Check canonical state
ckpt_count=$(ls "$DW1_OUT"/ckpt_*.bin 2>/dev/null | wc -l)
if [ "$ckpt_count" -lt 10 ]; then
    echo "FAIL: Only $ckpt_count checkpoints (expected at least 10)"
    exit 1
fi
echo "✓ $ckpt_count checkpoints created"

echo ""
echo "=== All basic tests passed ==="
echo "Run full oracle tests with tools/replay-check.sh"
```

**Make executable:**
```bash
chmod +x tools/test-linux.sh
```

**Run:**
```bash
export DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue
./tools/test-linux.sh
```

## Debugging Failed Tests

### If Replay Fails

Check the replay log:
```bash
cat /tmp/dw1-test-newgame.log
```

Look for:
- Divergence in canonical state
- Trap/crash
- Missing overlays

### If Window Doesn't Open

Check SDL3 is working:
```bash
# Simple SDL3 test
sdl3-test
```

Check Vulkan/OpenGL:
```bash
vulkaninfo  # For Vulkan
glxinfo     # For OpenGL
```

### If Audio Doesn't Play

Check audio system:
```bash
pactl info  # PulseAudio
# or
aplay -l    # ALSA
```

Test with mute disabled:
```bash
# DW1_MUTE=1 would mute audio
# Ensure it's not set
```

### If Controls Don't Work

Check SDL3 input:
```bash
# Test gamepad detection
sdl3-test --gamepad
```

### If Saves Don't Work

Check directory permissions:
```bash
ls -ld ~/.local/share/dw1-silicon
ls -ld ~/.config/dw1-silicon
```

## Performance Baseline

Run on macOS to establish baseline:

```bash
# On macOS
time DW1_REPLAY=oracle/replays/new-game.txt ./target/release/dw1
```

Run on Linux and compare:

```bash
# On Linux
time DW1_REPLAY=oracle/replays/new-game.txt ./target/release/dw1
```

Linux should be within 10% of macOS performance on similar hardware.

## Continuous Integration

Add to CI (if using GitHub Actions, GitLab CI, etc.):

**File:** `.github/workflows/test-linux.yml`

```yaml
name: Test Linux

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: recursive

      - name: Install dependencies
        run: |
          sudo apt update
          sudo apt install build-essential clang cmake python3-venv pkg-config libsdl3-dev libvulkan-dev

      - name: Set up Python
        run: |
          python3 -m venv .venv
          .venv/bin/pip install pyyaml cmake

      - name: Build
        run: ./tools/build-linux.sh

      - name: Install
        run: sudo ./tools/install-linux.sh

      - name: Test (requires disc - skip in CI)
        run: |
          echo "Skip full tests in CI (requires disc image)"
          # Just check binary exists
          test -x /usr/local/bin/dw1
```

## Deliverables

- [ ] All 43 certified replays pass on Linux
- [ ] Window mode works correctly
- [ ] Save system works
- [ ] Settings persist
- [ ] Audio works
- [ ] Controls work
- [ ] Performance matches macOS
- [ ] Crash handler produces useful output
- [ ] Test script created
- [ ] CI configuration added (optional)

## Known Issues to Track

Document any Linux-specific issues found during testing:

### Timing Differences
- VBlank timing may differ slightly between platforms
- Oracle may need tolerance for timing

### Audio Latency
- Linux audio stack may have different latency
- May need audio buffer size adjustments

### Gamepad Hotplug
- SDL3 gamepad hotplug behavior may differ
- Test with various gamepads

## Commit Message

```
test: verify Linux port with oracle tests

Run all 43 certified replays on Linux and verify they match the
macOS build. Add tools/test-linux.sh for basic regression testing.

Test results:
- All replays pass with identical canonical state
- Window mode works correctly
- Save system uses XDG directories
- Audio and input work as expected

The Linux port is now functionally equivalent to the macOS build.
```

## Notes

### Oracle Timing

The oracle uses VBlank counting, which should be platform-independent.
If timing issues arise, check the field rate implementation in window.rs.

### Random Number Generation

RNG is deterministic in the game, so replays should match exactly
regardless of platform. If they don't, there's a bug.

### Memory Layout

Memory layout differences between macOS (arm64) and Linux (x86_64)
shouldn't affect the game because all memory is managed through the
PS1 RAM simulation in crates/psyq/src/memory.rs.

### Porting Complete

After this phase, the Linux port is complete and ready for use!

## Next Steps

Consider future enhancements:
- Package for specific distros (.deb, .rpm)
- Flatpak distribution
- Snap package
- AUR package (Arch Linux)
- Documentation updates
- Performance optimization
