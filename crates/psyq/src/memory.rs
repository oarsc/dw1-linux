//! Native stand-ins for PS1 memory the game C addresses directly.
//!
//! - **PS1 RAM** (2 MB): fixed addresses in the decomp (`DW1_PS1_ADDR`: `GENERAL_BUFFER` at
//!   0x80010000, assets at known places inside overlay images, the overlays' load addresses)
//!   point here at the same offset (`addr & 0x1FFFFF`), so loaded files and the game's
//!   fixed-address reads agree. Only those regions are used; the rest of the game's memory is
//!   ordinary native memory.
//! - **The scratchpad** (1 KB at 0x1F800000): `getScratchAddr` (native `libetc.h`).
//!
//! Both are statics in the app's data segment, inside the GPU's link window
//! (docs/phase2-plan.md).

#![allow(non_upper_case_globals)]

/// PS1 main RAM size.
pub const PS1_RAM_SIZE: usize = 2 << 20;

/// PS1 scratchpad size.
pub const SCRATCHPAD_SIZE: usize = 1024;

#[repr(C, align(16))]
pub struct Ps1Ram(pub [u8; PS1_RAM_SIZE]);

#[repr(C, align(16))]
pub struct Scratchpad(pub [u8; SCRATCHPAD_SIZE]);

/// The stand-in for PS1 RAM, `dw1_ps1_ram` to the C.
#[unsafe(no_mangle)]
pub static mut dw1_ps1_ram: Ps1Ram = Ps1Ram([0; PS1_RAM_SIZE]);

/// The scratchpad, `dw1_scratchpad` to the C.
#[unsafe(no_mangle)]
pub static mut dw1_scratchpad: Scratchpad = Scratchpad([0; SCRATCHPAD_SIZE]);

/// The native address of PS1 RAM address `addr` (any segment: KUSEG, KSEG0, KSEG1).
pub fn ps1_ram_ptr(addr: u32) -> *mut u8 {
    (&raw mut dw1_ps1_ram)
        .cast::<u8>()
        .wrapping_add((addr & 0x1F_FFFF) as usize)
}

// ---- GPU packet links ----
//
// A PS1 primitive's tag and every ordering-table entry hold a 24-bit address (the low bits of
// a KSEG0 address), with 0xFFFFFF as the end marker. Natively a link is a 24-bit offset from
// the start of the app's `__DATA` segment, where all of the game's ordering tables and packet
// buffers live (game globals, the heap arena and the PS1 RAM stand-in are all statics there;
// docs/phase2-plan.md). Linking anything outside it stops the program.

use std::os::raw::{c_int, c_void};

/// ELF program header (64-bit), matching the layout the kernel and ld.so use.
#[repr(C)]
struct Elf64Phdr {
    p_type: u32,
    p_flags: u32,
    p_offset: u64,
    p_vaddr: u64,
    p_paddr: u64,
    p_filesz: u64,
    p_memsz: u64,
    p_align: u64,
}

/// `dl_phdr_info` as passed to `dl_iterate_phdr`'s callback.
#[repr(C)]
struct DlPhdrInfo {
    dlpi_addr: usize,
    dlpi_name: *const i8,
    dlpi_phdr: *const Elf64Phdr,
    dlpi_phnum: c_int,
}

/// `PT_LOAD`: a loadable segment.
const PT_LOAD: u32 = 1;

unsafe extern "C" {
    #[link_name = "__data_start"]
    static DATA_START: u8;
    /// Fallback: `_end` is the traditional BSS end symbol. We prefer the real segment limit
    /// from `dl_iterate_phdr`, but keep `_end` as fallback.
    #[link_name = "_end"]
    static DATA_END_FALLBACK: u8;
}

// `dl_iterate_phdr` from `<link.h>`, iterates over the program's loaded segments.
unsafe extern "C" {
    fn dl_iterate_phdr(
        callback: extern "C" fn(*mut DlPhdrInfo, usize, *mut c_void) -> c_int,
        data: *mut c_void,
    ) -> c_int;
}

/// The end-of-list link.
pub const LINK_END: u32 = 0x00FF_FFFF;

/// The real end of the app's `__DATA` segment, found by walking the ELF program headers with
/// `dl_iterate_phdr`. This is precise: `p_vaddr + p_memsz` of the `PT_LOAD` segment that
/// contains `__data_start` is the exact boundary of all mapped static data. Falls back to
/// `_end` if the iteration fails.
static DATA_END: std::sync::OnceLock<usize> = std::sync::OnceLock::new();

/// Callback for `dl_iterate_phdr`: finds the `PT_LOAD` segment containing `DATA_START` and
/// records its `p_vaddr + p_memsz` as the real data end.
extern "C" fn find_data_end_cb(
    info: *mut DlPhdrInfo,
    _size: usize,
    data: *mut c_void,
) -> c_int {
    let info = unsafe { &*info };
    let start = &raw const DATA_START as usize;
    let mut found_end: Option<usize> = None;

    for i in 0..info.dlpi_phnum as usize {
        let ph = unsafe { &*info.dlpi_phdr.add(i) };
        if ph.p_type != PT_LOAD {
            continue;
        }
        let seg_start = info.dlpi_addr.wrapping_add(ph.p_vaddr as usize);
        let seg_end = seg_start.wrapping_add(ph.p_memsz as usize);
        // Does this segment contain DATA_START?
        if start >= seg_start && start < seg_end {
            found_end = Some(seg_end);
            break;
        }
    }

    if let Some(end) = found_end {
        let out = unsafe { &mut *(data.cast::<usize>()) };
        *out = end;
        // Stop iterating: return non-zero.
        1
    } else {
        0
    }
}

/// The address range packet links can reach: the app's `__DATA` segment.
pub fn link_window() -> (usize, usize) {
    let start = &raw const DATA_START as usize;

    // Find the real segment end via dl_iterate_phdr, caching it.
    let end = DATA_END.get_or_init(|| {
        let mut end: usize = 0;
        unsafe {
            dl_iterate_phdr(find_data_end_cb, &mut end as *mut usize as *mut c_void);
        }
        // Fallback to `_end` if the iteration didn't find anything.
        if end == 0 {
            &raw const DATA_END_FALLBACK as usize
        } else {
            end
        }
    });

    // An offset must fit in 24 bits and never equal the end marker.
    assert!(
        *end - start < LINK_END as usize,
        "the __DATA segment ({:#x} bytes) is too big for 24-bit packet links",
        *end - start
    );
    (start, *end)
}

/// The link to `ptr`. Stops the program if `ptr` is outside the window: a stack local or a host
/// allocation can't be linked, and a truncated link would corrupt drawing silently.
pub fn link_of(ptr: *const u8) -> u32 {
    let (start, end) = link_window();
    let p = ptr as usize;
    if !(start..end).contains(&p) {
        crate::trap::stop(&format!(
            "psyq: GPU packet at {ptr:p} is outside the linkable data segment \
             {start:#x}..{end:#x} (docs/phase2-plan.md)"
        ));
    }
    (p - start) as u32
}

/// The native address of `link` (its low 24 bits), or null for the end marker.
pub fn ptr_of_link(link: u32) -> *mut u32 {
    let link = link & LINK_END;
    if link == LINK_END {
        return std::ptr::null_mut();
    }
    let (start, _) = link_window();
    (start + link as usize) as *mut u32
}

/// `dw1_gpu_link(p)` for the native `libgpu.h` macros: the 24-bit link to `p`.
#[unsafe(no_mangle)]
pub extern "C" fn dw1_gpu_link(p: *const u8) -> u32 {
    link_of(p)
}

/// `dw1_gpu_unlink(link)`: the packet a link points to (`nextPrim`).
#[unsafe(no_mangle)]
pub extern "C" fn dw1_gpu_unlink(link: u32) -> *mut u32 {
    ptr_of_link(link)
}

// ---- 32-bit pointers inside loaded data ----
//
// Some PS1 data holds addresses in 32-bit fields: libgs maps a TMD file in place, replacing
// its offsets with addresses (GsMapModelingData). Natively such a field holds 0x80000000 plus
// the target's offset into the same `__DATA` window, so it still fits 32 bits and reads like a
// KSEG0 address; every buffer it can point into (game statics, the heap arena, the PS1 RAM
// stand-in) is in the window (docs/phase2-plan.md).

/// The tag bit of an encoded 32-bit pointer.
pub const PTR32_TAG: u32 = 0x8000_0000;

/// `ptr` as a 32-bit pointer (stops the program if it's outside the window).
pub fn ptr32_of(ptr: *const u8) -> u32 {
    PTR32_TAG | link_of(ptr)
}

/// The native address of an encoded 32-bit pointer; null for 0.
pub fn ptr_of_ptr32(value: u32) -> *mut u8 {
    if value == 0 {
        return std::ptr::null_mut();
    }
    let (start, _) = link_window();
    (start + (value & !PTR32_TAG) as usize) as *mut u8
}

/// `dw1_ptr32_decode(v)` for the game C's reads of such fields.
#[unsafe(no_mangle)]
pub extern "C" fn dw1_ptr32_decode(value: u32) -> *mut u8 {
    ptr_of_ptr32(value)
}

/// `dw1_ptr32_encode(p)` for the game C's writes of such fields.
#[unsafe(no_mangle)]
pub extern "C" fn dw1_ptr32_encode(p: *const u8) -> u32 {
    ptr32_of(p)
}

#[cfg(test)]
mod tests {
    use super::*;

    static mut PACKET: [u32; 4] = [0; 4];

    #[test]
    fn links_round_trip_inside_the_data_segment() {
        for p in [
            (&raw const PACKET).cast::<u8>(),
            ps1_ram_ptr(0x8001_0000).cast_const(),
            (&raw const dw1_scratchpad).cast::<u8>(),
        ] {
            let link = link_of(p);
            assert!(link < LINK_END);
            assert_eq!(ptr_of_link(link).cast::<u8>().cast_const(), p);
        }
        assert!(ptr_of_link(LINK_END).is_null());
        assert!(ptr_of_link(0xFFFF_FFFF).is_null());
    }
}
