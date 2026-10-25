//! The scene-script bytes embedded at build time.
//!
//! `crates/dw1/build.rs` extracts the original SCNs to temporary text, applies the user's SCN
//! mods and embeds the assembled bytes. Without SCN mods, this module reports no embedded source
//! and the native game loads the original SCNs from the disc.

use std::ffi::c_void;

mod embedded {
    include!(concat!(env!("OUT_DIR"), "/embedded_scripts.rs"));
}

/// Whether the build embedded modded SCNs: 1 = yes, 0 = no (use the disc's original SCN files).
#[unsafe(no_mangle)]
pub extern "C" fn dw1_script_sources_status() -> i32 {
    if embedded::EMBEDDED.is_some() {
        1
    } else {
        eprintln!("dw1: no SCN mods embedded; using the disc's original SCN files");
        0
    }
}

/// Copy a byte range from the embedded script asset. `which`: 0 is DG, 1 is MAPHEAD.
/// Returns the number copied, which may be shorter at EOF, or -1 for invalid input/source.
#[unsafe(no_mangle)]
pub extern "C" fn dw1_script_source_read(
    which: i32,
    offset: u32,
    dest: *mut c_void,
    size: u32,
) -> i32 {
    let Some((dg, maphead)) = embedded::EMBEDDED else {
        return -1;
    };
    let Some(source) = (match which {
        0 => Some(dg),
        1 => Some(maphead),
        _ => None,
    }) else {
        return -1;
    };
    if dest.is_null() {
        return -1;
    }
    let Ok(offset) = usize::try_from(offset) else {
        return -1;
    };
    let Ok(size) = usize::try_from(size) else {
        return -1;
    };
    let Some(slice) = source.get(offset..) else {
        return 0;
    };
    let count = slice.len().min(size);
    // SAFETY: the C caller supplies a writable destination for `size` bytes; only `count <= size`
    // bytes are copied, and the embedded slice has a static lifetime.
    unsafe { std::ptr::copy_nonoverlapping(slice.as_ptr(), dest.cast::<u8>(), count) };
    i32::try_from(count).unwrap_or(-1)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_matches_the_embedded_scripts() {
        assert_eq!(
            dw1_script_sources_status(),
            if embedded::EMBEDDED.is_some() { 1 } else { 0 }
        );
    }

    #[test]
    fn embedded_scripts_can_be_read() {
        let Some((dg, maphead)) = embedded::EMBEDDED else {
            return;
        };
        assert!(dg.len() > 0x800);
        assert!(!maphead.is_empty());
        for (which, source) in [(0, dg), (1, maphead)] {
            let mut buffer = [0u8; 8];
            let count = dw1_script_source_read(which, 4, buffer.as_mut_ptr().cast(), 8);
            assert_eq!(count, 8);
            assert_eq!(&buffer, &source[4..12]);
        }
    }
}
