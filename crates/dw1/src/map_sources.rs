//! Edited maps embedded at build time.
//!
//! `crates/dw1/build.rs` extracts only maps named by mods to temporary text, applies the field
//! changes, and embeds the rebuilt bytes. With no mod for a map, the native C reads it from disc.

use std::ffi::{CStr, c_char, c_void};

mod embedded {
    include!(concat!(env!("OUT_DIR"), "/embedded_maps.rs"));
}

/// Copy an embedded map into `dest` when the build embedded it.
///
/// `name` is the `MapEntry.filename` (`TRAI00`). Returns 1 when copied and 0
/// when the map is not embedded (the caller then reads it from the disc).
#[unsafe(no_mangle)]
pub extern "C" fn dw1_map_embedded_read(name: *const c_char, dest: *mut c_void) -> i32 {
    if name.is_null() || dest.is_null() {
        return 0;
    }
    // SAFETY: the C caller passes the NUL-terminated MapEntry filename.
    let name = unsafe { CStr::from_ptr(name) }.to_bytes();
    for (key, bytes) in embedded::EMBEDDED_MAPS {
        if key.as_bytes().eq_ignore_ascii_case(name) {
            // SAFETY: `dest` is the map buffer (GENERAL_BUFFER_PTR); the embedded
            // map is a static slice, so only `bytes.len()` writable bytes are needed.
            unsafe {
                std::ptr::copy_nonoverlapping(bytes.as_ptr(), dest.cast::<u8>(), bytes.len());
            }
            return 1;
        }
    }
    0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn embedded_maps_are_readable() {
        for (name, bytes) in embedded::EMBEDDED_MAPS {
            assert!(!bytes.is_empty(), "{name} is empty");
            let cname = std::ffi::CString::new(*name).unwrap();
            let mut buffer = vec![0u8; bytes.len()];
            assert_eq!(
                dw1_map_embedded_read(cname.as_ptr(), buffer.as_mut_ptr().cast()),
                1
            );
            assert_eq!(buffer, *bytes);
        }
    }

    #[test]
    fn unknown_maps_are_not_embedded() {
        let cname = std::ffi::CString::new("NOPE_NEVER").unwrap();
        let mut buffer = [0u8; 4];
        assert_eq!(
            dw1_map_embedded_read(cname.as_ptr(), buffer.as_mut_ptr().cast()),
            0
        );
    }
}
