PLATFORM_RMA_TOOLS := platform-rma-tools-$(HOST_OS)
PLATFORM_RMA_TOOLS_ZIP := $(HOST_OUT)/$(PLATFORM_RMA_TOOLS).zip
PLATFORM_RMA_TOOLS_DIR := $(HOST_OUT)/$(PLATFORM_RMA_TOOLS)

ifeq ($(HOST_OS),windows)
    EXECUTABLE_SUFFIX = ".exe"
endif

$(PLATFORM_RMA_TOOLS_ZIP): action-authorization sign-efi-sig-list openssl
	$(hide) rm -rf $(PLATFORM_RMA_TOOLS_DIR)
	$(hide) mkdir -p $(PLATFORM_RMA_TOOLS_DIR)
	$(hide) $(ACP) -fp device/intel/build/generate_blpolicy_oemvars $(PLATFORM_RMA_TOOLS_DIR)/generate_blpolicy_oemvars.py
	$(hide) $(ACP) -fp $(HOST_OUT)/bin/action-authorization$(EXECUTABLE_SUFFIX) $(PLATFORM_RMA_TOOLS_DIR)/
	$(hide) $(ACP) -fp $(HOST_OUT)/bin/sign-efi-sig-list$(EXECUTABLE_SUFFIX) $(PLATFORM_RMA_TOOLS_DIR)/
	$(hide) $(ACP) -fp $(HOST_OUT)/bin/openssl$(EXECUTABLE_SUFFIX) $(PLATFORM_RMA_TOOLS_DIR)/openssl$(EXECUTABLE_SUFFIX)
	$(hide) $(ACP) -fp external/openssl/apps/openssl.cnf $(PLATFORM_RMA_TOOLS_DIR)/
	$(hide) tar czf $(PLATFORM_RMA_TOOLS_DIR)/efitools.tar.gz external/efitools
	$(hide) cd $(HOST_OUT) && zip -r $(PLATFORM_RMA_TOOLS).zip $(PLATFORM_RMA_TOOLS)

platform_rma_tools: $(PLATFORM_RMA_TOOLS_ZIP)
