# This provides the 'publish' and 'publish_ci' makefile targets.
#
# PUBLISH target:
# 	NOTE: When using the 'publish' target you MUST also use the 'dist'
# 	target.  The 'dist' target is a special target and unfortunately we
# 	can't just depend on the 'dist' target :(
# 	   e.g. 'make dist publish'
# 	   e.g. 'make droid dist publish'
#
# 	DO NOT DO: 'make publish' as it will not work
#
# PUBLISH_CI target:
# 	The 'publish_ci' target may be called by itself as it has a dependency
# 	on the one file we need.
# 	   e.g. 'make publish_ci'

publish_dest := $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)
publish_tool_dest :=  $(publish_dest)/../tools
publish_tool_destw := $(publish_tool_dest)/windows-x86/
publish_tool_destl := $(publish_tool_dest)/linux-x86/
publish_make_dir = $(if $(wildcard $1),,mkdir -p $1)

.PHONY: publish_mkdir_dest
publish_mkdir_dest:
	$(call publish_make_dir, $(publish_dest))

# Publish System symbols
PUB_SYSTEM_SYMBOLS := symbols.tar.gz

.PHONY: $(PUB_SYSTEM_SYMBOLS)
$(PUB_SYSTEM_SYMBOLS): $(systemtarball)
	@echo "Publish system symbols"
	$(hide) mkdir -p $(publish_dest)
	tar -czf $(publish_dest)/$@ $(PRODUCT_OUT)/symbols

.PHONY: publish_system_symbols
publish_system_symbols: $(PUB_SYSTEM_SYMBOLS)

# Publish Scripts needed for QEMU
PUB_QEMU_SCRIPTS := qemu_scripts.tar.gz

.PHONY: $(PUB_QEMU_SCRIPTS)
$(PUB_QEMU_SCRIPTS): $(scriptstarball)
	@echo "Publish scripts"
	$(hide) mkdir -p $(publish_dest)
	tar -czf $(publish_dest)/$@ $(PRODUCT_OUT)/scripts

.PHONY: publish_qemu_scripts
publish_qemu_scripts: $(PUB_QEMU_SCRIPTS)

.PHONY: publish_kernel_debug
# if kernel is not a prebuilt one
# and kernel is built locally
ifeq ($(TARGET_PREBUILT_KERNEL),)
ifneq ($(LOCAL_KERNEL_PATH),)
# Publish Kernel debug
PUB_KERNEL_DBG := vmlinux.bz2 System.map.bz2
PUB_KERNEL_DBG_PATH := $(publish_dest)/kernel
#PUB_KERNEL_DBG := $(addprefix $(PUB_KERNEL_DBG_PATH)/,$(PUB_KERNEL_DBG))

.PHONY: $(PUB_KERNEL_DBG)
$(PUB_KERNEL_DBG): $(LOCAL_KERNEL)
	@echo "Publish $(basename $(@F))"
	$(hide) mkdir -p $(PUB_KERNEL_DBG_PATH)
	$(hide) bzip2 -c $(LOCAL_KERNEL_PATH)/$(basename $(@F)) > $(PUB_KERNEL_DBG_PATH)/$@

PUB_KERNEL_MODULES = kernel_modules-$(TARGET_BUILD_VARIANT).tar.bz2

.PHONY: $(PUB_KERNEL_MODULES)
$(PUB_KERNEL_MODULES): $(LOCAL_KERNEL_PATH)/copy_modules
	@echo "Publish Kernel Modules"
	$(hide) mkdir -p $(PUB_KERNEL_DBG_PATH)
	-tar -cjf $(PUB_KERNEL_DBG_PATH)/$@ -C $(LOCAL_KERNEL_PATH)/lib/modules .

publish_kernel_debug: $(PUB_KERNEL_DBG) $(PUB_KERNEL_MODULES)
	@echo "Publish kernel debug: $(notdir $^)"
endif # $(LOCAL_KERNEL_PATH)
else
publish_kernel_debug:
	@echo "Publish kernel debug: skipped"
endif

# Publish Sofia LTE CMCC images
ifeq ($(PUBLISH_CMCC_IMG),true)
PUB_CMCC_ZIP := $(publish_dest)/$(notdir $(CMCC_TARGET))
$(PUB_CMCC_ZIP): publish_mkdir_dest $(CMCC_TARGET)
	$(hide) $(ACP) $(CMCC_TARGET) $@
endif

# Publish OS agnostic tag
ifneq ($(OS_AGNOSTIC_INFO),)
PUB_OSAGNOSTIC_TAG := $(publish_dest)/$(notdir $(OS_AGNOSTIC_INFO))
$(PUB_OSAGNOSTIC_TAG): publish_mkdir_dest $(OS_AGNOSTIC_INFO)
	$(hide)($(ACP) $(OS_AGNOSTIC_INFO) $@)
endif

# Publish kf4sbl
.PHONY: publish_kf4sbl
ifeq ($(KERNELFLINGER_SUPPORT_NON_EFI_BOOT),true)
publish_kf4sbl: publish_mkdir_dest kf4sbl-$(TARGET_BUILD_VARIANT)
	$(hide)($(ACP) $(BOARD_BOOTLOADER_IASIMAGE) $(publish_dest))
else
publish_kf4sbl:
	@echo "Publish kf4sbl: skipped"
endif

# Publish kf4sbl symbols files
.PHONY: publish_kf4sbl_symbols
ifeq ($(TARGET_BUILD_VARIANT:debug=)|$(KERNELFLINGER_SUPPORT_NON_EFI_BOOT),user|true)
publish_kf4sbl_symbols: publish_mkdir_dest kf4sbl-$(TARGET_BUILD_VARIANT) fb4sbl-$(TARGET_BUILD_VARIANT)
	$(hide)($(ACP) $(KF4SBL_SYMBOLS_ZIP) $(FB4SBL_SYMBOLS_ZIP) $(publish_dest))
else
publish_kf4sbl_symbols:
	@echo "Publish kf4sbl symbols: skipped"
endif

# Publish Firmware symbols
.PHONY: publish_firmware_symbols
FIRMWARE_SYMBOLS_FILE := $(TARGET_DEVICE)-symbols_firmware.zip
FIRMWARE_SYMBOLS_PATH := $(wildcard $(INTEL_PATH_HARDWARE)/$(TARGET_BOARD_PLATFORM)-fls/$(PRODUCT_MODEL)/symbols/*.elf)

publish_firmware_symbols: publish_mkdir_dest publish_flashfiles
ifneq ($(BUILD_OSAS),1) # prebuilt
	@echo "------------Publish prebuilt firmware symbols from $(FIRMWARE_SYMBOLS_PATH) -----------"
ifneq ($(FIRMWARE_SYMBOLS_PATH),)
	$(hide)-(zip -jry $(publish_dest)/$(FIRMWARE_SYMBOLS_FILE) $(FIRMWARE_SYMBOLS_PATH))
endif
else # built from source
	@echo "------------Publish compiled firmware symbols-----------"
	$(info $(BOOTLOADER_BIN_PATH) $(VMM_BUILD_OUT) $(SECVM_BUILD_DIR))
	$(hide)-(zip -jry $(publish_dest)/$(FIRMWARE_SYMBOLS_FILE) $(BOOTLOADER_BIN_PATH)/*/*.elf $(VMM_BUILD_OUT)/*/*.elf $(SECVM_BUILD_DIR)/*.elf $(THREADX_BUILD_DIR)/*.elf)
endif

# Are we doing an 'sdk' type lunch target
PUBLISH_SDK := $(strip $(filter sdk sdk_x86,$(TARGET_PRODUCT)))

ifndef PUBLISH_SDK

.PHONY: publish_flashfiles
ifdef INTEL_FACTORY_FLASHFILES_TARGET
publish_flashfiles: publish_mkdir_dest $(INTEL_FACTORY_FLASHFILES_TARGET)
	@$(ACP) $(INTEL_FACTORY_FLASHFILES_TARGET) $(publish_dest)
else
publish_flashfiles:
	@echo "Warning: Unable to fulfill publish_flashfiles makefile request"
endif

.PHONY:publish_ifwi
ifeq ($(USE_INTEL_FLASHFILES),false)
publish_ifwi:
	@echo "Warning: Unable to fulfill publish_ifwi makefile request"
endif

.PHONY: publish_liveimage
ifdef INTEL_LIVEIMAGE_TARGET
publish_liveimage: publish_mkdir_dest $(INTEL_LIVEIMAGE_TARGET)
	@$(ACP) $(INTEL_LIVEIMAGE_TARGET) $(publish_dest)
else
publish_liveimage:
	@echo "Warning: Unable to fulfill publish_liveimage makefile request"
endif

.PHONY: publish_gptimage
ifdef GPTIMAGE_BIN
ifeq ($(COMPRESS_GPTIMAGE), true)
publish_gptimage: publish_mkdir_dest $(GPTIMAGE_BIN)
	@echo compress $(GPTIMAGE_BIN) into $(GPTIMAGE_GZ)
	@gzip -fk $(GPTIMAGE_BIN)
	@$(ACP) $(GPTIMAGE_GZ) $(publish_dest)
else # COMPRESS_GPTIMAGE is not true
publish_gptimage: publish_mkdir_dest $(GPTIMAGE_BIN)
	@$(ACP) $(GPTIMAGE_BIN) $(publish_dest)
endif # COMPRESS_GPTIMAGE
ifdef CRAFFIMAGE_BIN
	$(TOP)/$(INTEL_PATH_BUILD)/createcraffimage.py --image $(GPTIMAGE_BIN)
	@$(ACP) $(CRAFFIMAGE_BIN) $(publish_dest)
endif
else  # GPTIMAGE_BIN is not defined
publish_gptimage:
	@echo "Warning: Unable to fulfill publish_gptimage makefile request"
endif # GPTIMAGE_BIN

.PHONY: publish_gptimage_var
ifeq ($(BUILD_GPTIMAGE), true)
publish_gptimage_var: publish_gptimage
	@echo "building gptimages ..."
else  # GPTIMAGE_BIN is not defined
publish_gptimage_var:
	@echo "skip build gptimage"
endif # GPTIMAGE_BIN

.PHONY: publish_androidia_image
ifdef ANDROID_IA_IMAGE
publish_androidia_image: publish_mkdir_dest $(ANDROID_IA_IMAGE)
	@$(ACP) $(ANDROID_IA_IMAGE) $(publish_dest)
else
publish_androidia_image:
	@echo "Warning: Unable to fulfill publish_androidia_image makefile request"
endif

.PHONY: publish_otapackage
publish_otapackage: publish_mkdir_dest $(INTERNAL_OTA_PACKAGE_TARGET)
	@$(ACP) $(INTERNAL_OTA_PACKAGE_TARGET) $(publish_dest)

.PHONY: publish_ota_targetfiles
publish_ota_targetfiles: publish_mkdir_dest $(BUILT_TARGET_FILES_PACKAGE)
	@$(ACP) $(BUILT_TARGET_FILES_PACKAGE) $(publish_dest)

.PHONY: publish_ota_flashfile
ifneq ($(PUBLISH_CONF),)
BUILDBOT_PUBLISH_DEPS := $(shell python -c 'import json,os ; print " ".join(json.loads(os.environ["PUBLISH_CONF"]).get("$(TARGET_BUILD_VARIANT)",[]))')

# Translate buildbot target to makefile target
publish_ota_flashfile: $(BUILDBOT_PUBLISH_DEPS)

full_ota: publish_otapackage
full_ota_flashfile:
ota_target_files: publish_ota_targetfiles
system_img:
else
publish_ota_flashfile:
	@echo "Do not publish ota_flashfile"
endif # PUBLISH_CONF

PUBLISH_CI_FILES := out/dist/fastboot out/dist/adb
.PHONY: publish_ci
ifeq ($(ANDROID_AS_GUEST), true)
publish_ci: aic
	@echo Publish AIC docker images...
	$(hide) mkdir -p $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)
	$(hide) cp $(PRODUCT_OUT)/$(TARGET_AIC_FILE_NAME) $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)
else # ANDROID_AS_GUEST
ifeq ($(KERNELFLINGER_SUPPORT_NON_EFI_BOOT), false)
publish_ci: publish_liveimage publish_ota_flashfile publish_gptimage publish_grubinstaller publish_ifwi publish_firmware_symbols $(PUB_OSAGNOSTIC_TAG) $(PUB_CMCC_ZIP) $(PLATFORM_RMA_TOOLS_ZIP)
	$(if $(wildcard $(publish_dest)), \
	  $(foreach f,$(PUBLISH_CI_FILES), \
	    $(if $(wildcard $(f)),$(ACP) $(f) $(publish_dest);,)),)
	@$(hide) mkdir -p $(publish_tool_destl)
	@$(hide) $(ACP) $(PLATFORM_RMA_TOOLS_ZIP) $(publish_tool_destl)


.PHONY: publish_windows_tools
publish_windows_tools: $(PLATFORM_RMA_TOOLS_CROSS_ZIP)
	@$(hide) mkdir -p $(publish_tool_destw)
	@$(hide) $(ACP) $(PLATFORM_RMA_TOOLS_CROSS_ZIP) $(publish_tool_destw)
else
publish_ci: publish_liveimage publish_ota_flashfile publish_gptimage_var publish_grubinstaller publish_ifwi publish_kf4sbl publish_firmware_symbols $(PUB_OSAGNOSTIC_TAG) $(PUB_CMCC_ZIP)
	$(if $(wildcard $(publish_dest)), \
	  $(foreach f,$(PUBLISH_CI_FILES), \
	    $(if $(wildcard $(f)),$(ACP) $(f) $(publish_dest);,)),)
endif
endif # ANDROID_AS_GUEST

else # !PUBLISH_SDK
# Unfortunately INTERNAL_SDK_TARGET is always defined, so its existence does
# not indicate that we are building the SDK

.PHONY: publish_ci
publish_ci: publish_sdk_target


.PHONY: publish_sdk_target
publish_sdk_target: publish_mkdir_dest $(INTERNAL_SDK_TARGET)
	@$(ACP) $(INTERNAL_SDK_TARGET) $(publish_dest)


endif # !PUBLISH_SDK

# We need to make sure our 'publish' target depends on the other targets so
# that it will get done at the end.  Logic copied from build/core/distdir.mk
PUBLISH_GOALS := $(strip $(filter-out publish publish_ci,$(MAKECMDGOALS)))
PUBLISH_GOALS := $(strip $(filter-out $(INTERNAL_MODIFIER_TARGETS),$(PUBLISH_GOALS)))
ifeq (,$(PUBLISH_GOALS))
# The commandline was something like "make publish" or "make publish showcommands".
# Add a dependency on a real target.
PUBLISH_GOALS := $(DEFAULT_GOAL)
endif

.PHONY: publish_grubinstaller
ifeq ($(ENABLE_GRUB_INSTALLER),true)
ifneq ($(TARGET_BUILD_VARIANT),user)
publish_grubinstaller: publish_mkdir_dest $(PROJECT_CELADON-EFI)
	echo compress $(PROJECT_CELADON-EFI) into $(PROJECT_CELADON-EFI).gz
	gzip -f $(PROJECT_CELADON-EFI)
	@$(ACP) $(PROJECT_CELADON-EFI).gz $(publish_dest)
else
publish_grubinstaller:
	echo "Do not publish grub installer in user mode"
endif
endif # ENABLE_GRUB_INSTALLER

.PHONY: publish
ifeq ($(ANDROID_AS_GUEST), true)
publish: aic
	@echo Publish AIC docker images...
	$(hide) mkdir -p $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)
	$(hide) cp $(PRODUCT_OUT)/$(TARGET_AIC_FILE_NAME) $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)
else # ANDROID_AS_GUEST
publish: publish_mkdir_dest $(PUBLISH_GOALS) publish_ifwi publish_gptimage_var publish_firmware_symbols $(PUB_OSAGNOSTIC_TAG) publish_kf4sbl publish_kf4sbl_symbols $(PUB_CMCC_ZIP) publish_androidia_image publish_grubinstaller publish_kernel_debug
	@$(ACP) out/dist/* $(publish_dest)
endif # ANDROID_AS_GUEST
