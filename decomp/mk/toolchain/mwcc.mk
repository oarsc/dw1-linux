MWCCWRAP ?= bin/mwccwrap/mwccwrap.exe
MWCC_OPT_LEVEL ?= 4
MWCCWRAP_FLAGS ?= -dll "bin/cc_mips/cc_mips_40.dll"
MWCCWRAP_FLAGS += -O$(MWCC_OPT_LEVEL) -sdata 8 -Werror -requireprotos -gccincludes \
		  -lang c -Cpp_exceptions off -RTTI off -multibyteaware \
		  -codepage 932

export MWCIncludes =

WIBO ?= bin/wibo-x86_64

METROWRAP ?= bin/metrowrap/mw
METROWRAP_FLAGS ?= --use-wibo --wibo-path $(WIBO)
METROWRAP_FLAGS += --mwcc-path $(MWCCWRAP) --split-sections \
		 --elf-flags 0x00001001 \
		 --as-march r3000 \
		 --macro-inc-path include/macro.inc \
		 --target-encoding windows-31j

# objdiff only merges .rodata.*/.data.*/.sdata.* sections under the plain name
# when there are at least two of them. The expected objects also contain an
# empty plain section, so add one here too, or a file with a single symbol in
# one of them is never compared. The empty sections are discarded at link time.
$(BUILD_DIR)/%.c.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(CPPFLAGS) $(DEPFLAGS) $<
	$(METROWRAP) -o $@ $(METROWRAP_FLAGS) $(MWCCWRAP_FLAGS) $(CPPFLAGS) $<
	@$(OBJCOPY) --add-section .rodata=/dev/null \
				--set-section-flags .rodata=alloc,load,readonly,data \
				--add-section .data=/dev/null \
				--set-section-flags .data=alloc,load,data \
				--add-section .sdata=/dev/null \
				--set-section-flags .sdata=alloc,load,data $@

$(BUILD_DIR)/src/fish/fish.c.o: MWCCWRAP_FLAGS += -pragma "optimize_for_size on"
