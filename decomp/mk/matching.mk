EXPECTED_DIR := expected/$(VERSION)

OBJDIFF ?= bin/objdiff-cli-linux-x86_64

compare:
	@tools/cmp_bins.sh $(DISK_DIR) $(BUILD_DIR) $(EXE_NAME) \
		$(OVERLAY:%=%_REL.BIN)

expected: $(OBJ)
	rm -rf $(EXPECTED_DIR)
	@mkdir -p $(EXPECTED_DIR)
	cp -r $(BUILD_DIR)/asm $(EXPECTED_DIR)/asm
	$(if $(wildcard $(BUILD_DIR)/src),cp -r $(BUILD_DIR)/src $(EXPECTED_DIR)/src)

objdiff: expected
	$(PYTHON) tools/objdiff/objdiff_generate.py tools/objdiff/config.yaml \
		$(BUILD_DIR)/src $(EXPECTED_DIR)/asm

report: objdiff
	$(OBJDIFF) report generate \
		--config combineTextSections=false > $(BUILD_DIR)/report.json

# Fix objdiff jump table mismatches by making jump table labels local
C_ASM_OBJ := $(patsubst $(BUILD_DIR)/src/%.c.o,$(BUILD_DIR)/asm/%.s.o,$(filter %.c.o,$(OBJ)))
$(C_ASM_OBJ): ASFLAGS += -Wa,--defsym,LOCAL_JLABELS=1

# Add a C file's small data in the main executable to its objdiff target
c_sdata_asm = $(wildcard $(1:$(BUILD_DIR)/asm/%.s.o=$(ASM_DIR)/main/data/%.sdata.s))
$(foreach o,$(C_ASM_OBJ),$(foreach s,$(call c_sdata_asm,$(o)),$(eval $(o): $(s))))
$(foreach o,$(C_ASM_OBJ),$(foreach s,$(call c_sdata_asm,$(o)),$(eval $(o): ASFLAGS += -Wa,$(s))))
