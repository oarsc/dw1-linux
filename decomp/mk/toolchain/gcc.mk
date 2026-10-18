GCC_FLAGS = -g -Wall -Wextra -std=c99 -Os $(ARCHFLAGS) -G8 \
	    -ffunction-sections -fdata-sections -fno-common \
	    -fno-zero-initialized-in-bss -fno-builtin \
	    -fno-strict-aliasing -fwrapv -fno-tree-switch-conversion \
	    -finput-charset=UTF-8 -fexec-charset=CP932

$(BUILD_DIR)/%.c.o: %.c
	@mkdir -p $(dir $@)
	$(CC) -c $(GCC_FLAGS) $(CPPFLAGS) -MMD -MP -MF $(@:.o=.d) -MT $@ -o $@ $<
