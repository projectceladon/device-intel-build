PLATFORM_RMA_TOOLS := platform-rma-tools-$(HOST_OS)
PLATFORM_RMA_TOOLS_CROSS := platform-rma-tools-$(HOST_CROSS_OS)
PLATFORM_RMA_TOOLS_ZIP := $(HOST_OUT)/$(PLATFORM_RMA_TOOLS).zip
PLATFORM_RMA_TOOLS_CROSS_ZIP := $(HOST_CROSS_OUT)/$(PLATFORM_RMA_TOOLS_CROSS).zip
PLATFORM_RMA_TOOLS_DIR := $(HOST_OUT)/$(PLATFORM_RMA_TOOLS)
PLATFORM_RMA_TOOLS_CROSS_DIR := $(HOST_CROSS_OUT)/$(PLATFORM_RMA_TOOLS_CROSS)

EXECUTABLE_CROSS_SUFFIX = ".exe"


ifeq ($(SOC_FIRMWARE_TYPE),slb)

ifeq ($(HOST_OS),windows)
RMA_TO_COPY := key_maker/bin/win32/key_maker.exe signing_module/bin/win32/sec_signing.exe signing_module/bin/win32/signing_module.dll
else
RMA_TO_COPY := key_maker/bin/linux/key_maker32 signing_module/bin/linux/m32/sec_signing signing_module/bin/linux/m32/libsigningmodule.so
endif
RMA_TO_COPY := $(addprefix $(INTEL_PATH_HARDWARE)/mrd-3gr-sofia/secure_vm/src/security_framework/tools/,$(RMA_TO_COPY))

RMA_TO_COPY += device/intel/$(TARGET_PROJECT)/security/oem_oak_flag.bin $(HOST_OUT)/bin/action-authorization$(EXECUTABLE_SUFFIX) $(HOST_OUT)/bin/openssl$(EXECUTABLE_SUFFIX) $(INTEL_PATH_VENDOR)/external/openssl/apps/openssl.cnf

$(PLATFORM_RMA_TOOLS_ZIP): action-authorization openssl $(RMA_TO_COPY)
	$(hide) rm -rf $(PLATFORM_RMA_TOOLS_DIR) $(PLATFORM_RMA_TOOLS_ZIP)
	$(hide) mkdir -p $(PLATFORM_RMA_TOOLS_DIR)
	$(hide) $(ACP) -fp $(RMA_TO_COPY) $(PLATFORM_RMA_TOOLS_DIR)
	$(hide) cd $(HOST_OUT) && zip -r $(PLATFORM_RMA_TOOLS).zip $(PLATFORM_RMA_TOOLS)

else

$(PLATFORM_RMA_TOOLS_ZIP): action-authorization sign-efi-sig-list openssl
	$(hide) rm -rf $(PLATFORM_RMA_TOOLS_DIR)
	$(hide) mkdir -p $(PLATFORM_RMA_TOOLS_DIR)
	$(hide) $(ACP) -fp $(INTEL_PATH_BUILD)/generate_blpolicy_oemvars $(PLATFORM_RMA_TOOLS_DIR)/generate_blpolicy_oemvars.py
	$(hide) $(ACP) -fp $(HOST_OUT)/bin/action-authorization$(EXECUTABLE_SUFFIX) $(PLATFORM_RMA_TOOLS_DIR)/
	$(hide) $(ACP) -fp $(HOST_OUT)/bin/sign-efi-sig-list$(EXECUTABLE_SUFFIX) $(PLATFORM_RMA_TOOLS_DIR)/
	$(hide) $(ACP) -fp $(HOST_OUT)/bin/openssl$(EXECUTABLE_SUFFIX) $(PLATFORM_RMA_TOOLS_DIR)/openssl$(EXECUTABLE_SUFFIX)
	$(hide) $(ACP) -fp $(INTEL_PATH_VENDOR)/external/openssl/apps/openssl.cnf $(PLATFORM_RMA_TOOLS_DIR)/
	$(hide) tar czf $(PLATFORM_RMA_TOOLS_DIR)/efitools.tar.gz external/efitools
	$(hide) cd $(HOST_OUT) && zip -r $(PLATFORM_RMA_TOOLS).zip $(PLATFORM_RMA_TOOLS)

endif


ifneq (,$(findstring cht,$(TARGET_PRODUCT)))
$(PLATFORM_RMA_TOOLS_CROSS_ZIP): host_cross_action-authorization host_cross_sign-efi-sig-list host_cross_openssl
	$(hide) rm -rf $(PLATFORM_RMA_TOOLS_CROSS_DIR)
	$(hide) mkdir -p $(PLATFORM_RMA_TOOLS_CROSS_DIR)
	$(hide) $(ACP) -fp $(INTEL_PATH_BUILD)/generate_blpolicy_oemvars $(PLATFORM_RMA_TOOLS_CROSS_DIR)/generate_blpolicy_oemvars.py
	$(hide) $(ACP) -fp $(HOST_CROSS_OUT)/bin/action-authorization$(EXECUTABLE_CROSS_SUFFIX) $(PLATFORM_RMA_TOOLS_CROSS_DIR)/
	$(hide) $(ACP) -fp $(HOST_CROSS_OUT)/bin/sign-efi-sig-list$(EXECUTABLE_CROSS_SUFFIX) $(PLATFORM_RMA_TOOLS_CROSS_DIR)/
	$(hide) $(ACP) -fp $(HOST_CROSS_OUT)/bin/openssl$(EXECUTABLE_CROSS_SUFFIX) $(PLATFORM_RMA_TOOLS_CROSS_DIR)/openssl$(EXECUTABLE_CROSS_SUFFIX)
	$(hide) $(ACP) -fp $(INTEL_PATH_VENDOR)/external/openssl/apps/openssl.cnf $(PLATFORM_RMA_TOOLS_CROSS_DIR)/
	$(hide) tar czf $(PLATFORM_RMA_TOOLS_CROSS_DIR)/efitools.tar.gz external/efitools
	$(hide) cd $(HOST_CROSS_OUT) && zip -r $(PLATFORM_RMA_TOOLS_CROSS).zip $(PLATFORM_RMA_TOOLS_CROSS)

else
$(PLATFORM_RMA_TOOLS_CROSS_ZIP):
	$(info "cross compilation is not available on this target")
	touch $(PLATFORM_RMA_TOOLS_CROSS_ZIP)
endif
platform_rma_tools:

host_cross_platform_rma_tools:
