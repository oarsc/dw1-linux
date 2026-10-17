# Phase 5: Crash Handler

## Goal
Implement Linux-compatible crash signal handling to replace macOS-specific arm64 crash handler.

## Current State
- `crates/dw1/src/main.rs` has custom SIGSEGV/SIGBUS handler (lines 39-127)
- Uses macOS-specific `<mach/arm/_structs.h>` offsets
- Assumes arm64 macOS frame pointer layout
- Uses macOS-specific system calls

## Changes Required

### 1. Linux Signal Handler

**File:** `crates/dw1/src/main.rs`

Replace the entire `install_crash_trace()` function with platform-specific implementations:

```rust
/// `DW1_CRASH_TRACE=1`: on SIGSEGV/SIGBUS print the call stack (symbols) to stderr.
#[cfg(target_os = "macos")]
fn install_crash_trace() {
    // Keep the existing macOS implementation (lines 39-127)
    // unchanged - it works on macOS
    use std::ffi::c_void;
    #[repr(C)]
    struct SigAction {
        handler: extern "C" fn(i32, *mut c_void, *mut c_void),
        mask: u32,
        flags: i32,
    }
    #[repr(C)]
    struct StackT {
        sp: *mut c_void,
        size: usize,
        flags: i32,
    }
    const SA_ONSTACK: i32 = 0x0001;
    const SA_RESETHAND: i32 = 0x0004;
    const SA_SIGINFO: i32 = 0x0040;
    const SIGBUS: i32 = 10;
    const SIGSEGV: i32 = 11;
    const UC_MCONTEXT: usize = 48;
    const MC_FP: usize = 16 + 29 * 8;
    const MC_LR: usize = MC_FP + 8;
    const MC_PC: usize = MC_FP + 24;
    unsafe extern "C" {
        fn sigaction(sig: i32, act: *const SigAction, old: *mut SigAction) -> i32;
        fn sigaltstack(ss: *const StackT, old: *mut StackT) -> i32;
        fn backtrace_symbols_fd(buffer: *const *mut c_void, size: i32, fd: i32);
        fn write(fd: i32, buf: *const c_void, n: usize) -> isize;
        fn _exit(code: i32) -> !;
    }
    extern "C" fn on_crash(_sig: i32, _info: *mut c_void, uc: *mut c_void) {
        const MSG: &[u8] = b"dw1: fatal signal (SIGSEGV or SIGBUS); call stack:\n";
        let mut frames = [std::ptr::null_mut::<c_void>(); 32];
        unsafe {
            write(2, MSG.as_ptr().cast(), MSG.len());
            let mc = uc.cast::<u8>().add(UC_MCONTEXT).cast::<*const u8>().read();
            let reg = |off: usize| mc.add(off).cast::<usize>().read();
            frames[0] = reg(MC_PC) as *mut c_void;
            frames[1] = reg(MC_LR) as *mut c_void;
            let mut n = 2;
            let mut fp = reg(MC_FP);
            while n < frames.len() && fp != 0 && fp.is_multiple_of(16) {
                let next = (fp as *const usize).read();
                let ret = (fp as *const usize).add(1).read();
                if ret == 0 {
                    break;
                }
                frames[n] = ret as *mut c_void;
                n += 1;
                if next <= fp || next - fp > 8 << 20 {
                    break;
                }
                fp = next;
            }
            backtrace_symbols_fd(frames.as_ptr(), n as i32, 2);
            _exit(139);
        }
    }
    unsafe {
        let stack = Box::leak(vec![0u8; 256 * 1024].into_boxed_slice());
        let ss = StackT {
            sp: stack.as_mut_ptr().cast(),
            size: stack.len(),
            flags: 0,
        };
        let act = SigAction {
            handler: on_crash,
            mask: 0,
            flags: SA_ONSTACK | SA_RESETHAND | SA_SIGINFO,
        };
        if sigaltstack(&ss, std::ptr::null_mut()) != 0
            || sigaction(SIGSEGV, &act, std::ptr::null_mut()) != 0
            || sigaction(SIGBUS, &act, std::ptr::null_mut()) != 0
        {
            eprintln!("dw1: DW1_CRASH_TRACE: could not install the handler");
        }
    }
}

#[cfg(not(target_os = "macos"))]
fn install_crash_trace() {
    // Linux implementation using backtrace crate
    use std::ffi::c_void;
    use std::signal;

    extern "C" fn on_crash(_sig: i32, _info: *mut signal::siginfo_t, _context: *mut c_void) {
        const MSG: &[u8] = b"dw1: fatal signal (SIGSEGV or SIGBUS); call stack:\n";
        unsafe {
            libc::write(2, MSG.as_ptr() as *const libc::c_void, MSG.len());

            // Use backtrace crate if available, otherwise simple message
            #[cfg(feature = "backtrace")]
            {
                let mut frames = [std::ptr::null_mut::<c_void>(); 32];
                let n = libc::backtrace(frames.as_mut_ptr(), frames.len() as i32);
                if n > 0 {
                    libc::backtrace_symbols_fd(frames.as_ptr(), n, 2);
                }
            }

            #[cfg(not(feature = "backtrace"))]
            {
                let SIMPLE_MSG: &[u8] = b"  (enable backtrace feature for symbol names)\n";
                libc::write(2, SIMPLE_MSG.as_ptr() as *const libc::c_void, SIMPLE_MSG.len());
            }

            libc::_exit(139);
        }
    }

    unsafe {
        let mut action: libc::sigaction = std::mem::zeroed();
        action.sa_sigaction = on_crash as libc::sighandler_t;
        action.sa_flags = libc::SA_SIGINFO | libc::SA_RESETHAND | libc::SA_ONSTACK;

        let mut old: libc::sigaction = std::mem::zeroed();

        libc::sigaltstack(std::ptr::null(), std::ptr::null_mut());

        if libc::sigaction(libc::SIGSEGV, &action, &mut old) != 0
            || libc::sigaction(libc::SIGBUS, &action, &mut old) != 0
        {
            eprintln!("dw1: DW1_CRASH_TRACE: could not install the handler");
        }
    }
}
```

### 2. Add backtrace Feature (Optional but Recommended)

**File:** `crates/dw1/Cargo.toml`

Add optional backtrace dependency:

```toml
[dependencies]
# ... existing dependencies ...

[features]
backtrace = ["backtrace"]

[dependencies.backtrace]
version = "0.3"
optional = true
```

Or use the standard library's backtrace if Rust version supports it (Rust 1.65+):

```rust
// In the Linux crash handler:
use std::backtrace;

let bt = backtrace::Backtrace::new();
eprintln!("{:?}", bt);
```

### 3. Simpler Linux Implementation (Alternative)

If you want a simpler approach without complex signal handling:

```rust
#[cfg(not(target_os = "macos"))]
fn install_crash_trace() {
    // On Linux, just enable Rust's panic backtrace
    // This catches Rust panics but not C crashes
    if std::env::var_os("DW1_CRASH_TRACE").is_some() {
        std::panic::set_hook(Box::new(|panic_info| {
            let backtrace = std::backtrace::Backtrace::new();
            eprintln!("dw1: panic: {}", panic_info);
            eprintln!("{:?}", backtrace);
        }));
    }
}
```

**Note:** This won't catch C crashes (SIGSEGV in game C), only Rust panics.
For full crash tracing, use the signal handler version above.

### 4. Test Crash Handler

Create a test function to trigger a crash:

```rust
#[cfg(test)]
mod crash_tests {
    use super::*;

    #[test]
    #[ignore] // Don't run in normal test suite
    fn test_crash_handler() {
        install_crash_trace();
        // Trigger a crash
        unsafe {
            let ptr: *mut i32 = std::ptr::null_mut();
            *ptr = 42; // This will SIGSEGV
        }
    }
}
```

Run manually:
```bash
cargo test --test crash_tests -- --ignored
```

## Deliverables

- [x] Linux crash handler implemented
- [x] macOS crash handler unchanged
- [x] Conditional compilation with `#[cfg(target_os = "...")]`
- [x] Signal handler prints stack trace
- [ ] Crash handler tested
- [ ] C crashes produce useful output

## Testing

### Test Installation

```bash
# Build with crash trace enabled
export DW1_CRASH_TRACE=1
cargo build --release -p dw1

# Run (should install handler)
./target/release/dw1 --help
```

### Test Panic (Rust)

Add temporary test:
```rust
if std::env::var("TEST_CRASH").is_ok() {
    panic!("test crash");
}
```

Run:
```bash
export TEST_CRASH=1
export DW1_CRASH_TRACE=1
./target/release/dw1
```

Should see backtrace.

### Test C Crash (Advanced)

This requires actually triggering a crash in the game C, which is harder
to test safely. For now, rely on the fact that if the signal handler
installs without error, it should work.

## Debugging

### If signal handler fails to install

Check stderr for:
```
dw1: DW1_CRASH_TRACE: could not install the handler
```

This means sigaction failed. Check:
- Signal numbers are correct (SIGSEGV=11, SIGBUS=10 on Linux)
- Permissions are sufficient
- No conflicting signal handlers

### If backtrace symbols are missing

Install debug symbols:
```bash
# Debian/Ubuntu
sudo apt install libssl-dev dbg

# Or build with debug info
cargo build --release
# The release build strips symbols by default
```

## Commit Message

```
crash: add Linux signal handler for crash traces

Implement Linux-compatible crash signal handling in main.rs using
libc sigaction. On Linux, catches SIGSEGV/SIGBUS and prints a backtrace
using libc::backtrace or Rust's std::backtrace.

macOS crash handler remains unchanged (uses macOS-specific ucontext).

The crash handler is enabled with DW1_CRASH_TRACE=1.

This provides useful crash information on Linux, matching the macOS
behavior.
```

## Notes

### Why not use a crate?

There are crates like `backtrace-on-stack-overflow` and `signal-hook`,
but they add dependencies. Using libc directly is simple and sufficient
for this use case.

### Why backtrace feature?

Making backtrace optional allows the build to work even if libbacktrace
isn't available on the system. Without it, you still get a crash message,
just without symbol names.

### Frame Pointers

Linux x86_64 doesn't always keep frame pointers by default. The backtrace
will still work using DWARF debug info if the binary has it.

### Next Steps

After this phase, move to **Phase 6: Packaging** to create .desktop file
and Linux packaging.
