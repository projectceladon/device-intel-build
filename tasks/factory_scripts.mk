# -----------------------------------------------------------------
# Factory Scripts

# FIXME why the conversion to lowercase??
BUILD_ID_LC := $(shell echo $(BUILD_ID) | tr A-Z a-z)
FACTORY_SCRIPTS_PACKAGE_TARGET := $(PRODUCT_OUT)/$(TARGET_PRODUCT)-$(BUILD_ID_LC)-factory.tgz
intermediates := $(call intermediates-dir-for,PACKAGING,factory_scripts)
FACTORY_SCRIPTS_BOOTLOADER_IMAGE := $(intermediates)/bootloader-$(TARGET_PRODUCT)-$(FILE_NAME_TAG).bin
FACTORY_SCRIPTS_FASTBOOT_IMAGE := $(intermediates)/fastboot-$(TARGET_PRODUCT)-$(FILE_NAME_TAG).img
FACTORY_SCRIPTS_FASTBOOT_USB := $(intermediates)/fastboot-usb-$(TARGET_PRODUCT)-$(FILE_NAME_TAG).img
FACTORY_SCRIPTS_OEMVARS := $(if $(BOARD_OEM_VARS_FILE),--oemvars $(BOARD_OEM_VARS_FILE))

# For legacy boot, we need to include the MBR boot block
ifeq ($(TARGET_USE_SYSLINUX),true)
	factory_scripts_mbr_boot_block = $(BOARD_MBR_BLOCK_BIN)
	factory_scripts_mbr_boot_block_option = --mbr $(BOARD_MBR_BLOCK_BIN)
else
	factory_scripts_mbr_boot_block :=
	factory_scripts_mbr_boot_block_option :=
endif

# We could just get the fastboot.img and bootloader blobs from the $OUT
# directory, but let's make sure these scripts don't bit-rot as they are
# critical for release workflow.

ifeq ($(TARGET_USE_SYSLINUX),true)

# legacy boot requires a premade bootloader using syslinux
# and cannot be generated from target files.
# hence this "special" treatment.
$(FACTORY_SCRIPTS_BOOTLOADER_IMAGE): \
		$(PRODUCT_OUT)/bootloader \
		| $(ACP) \

	mkdir -p $(dir $@)
	$(hide) $(ACP) -f $(PRODUCT_OUT)/bootloader $(FACTORY_SCRIPTS_BOOTLOADER_IMAGE)

else

$(FACTORY_SCRIPTS_BOOTLOADER_IMAGE): \
		$(BUILT_TARGET_FILES_PACKAGE) \
		device/intel/build/releasetools/bootloader_from_target_files \

	mkdir -p $(dir $@)
	$(hide) device/intel/build/releasetools/bootloader_from_target_files \
		--verbose $(BUILT_TARGET_FILES_PACKAGE) $@

endif

$(FACTORY_SCRIPTS_FASTBOOT_IMAGE): \
		$(BUILT_TARGET_FILES_PACKAGE) \
		device/intel/build/releasetools/fastboot_from_target_files \

	mkdir -p $(dir $@)
	$(hide) MKBOOTIMG=$(BOARD_CUSTOM_MKBOOTIMG) \
		device/intel/build/releasetools/fastboot_from_target_files \
		--verbose $(BUILT_TARGET_FILES_PACKAGE) $@

$(FACTORY_SCRIPTS_FASTBOOT_USB): \
		$(BUILT_TARGET_FILES_PACKAGE) \
		device/intel/build/releasetools/fastboot_usb_from_target_files \

	mkdir -p $(dir $@)
	$(hide) MKBOOTIMG=$(BOARD_CUSTOM_MKBOOTIMG) \
		device/intel/build/releasetools/fastboot_usb_from_target_files \
		--verbose $(BUILT_TARGET_FILES_PACKAGE) $@

$(FACTORY_SCRIPTS_PACKAGE_TARGET): \
                device/intel/build/generate_factory_images \
		$(FACTORY_SCRIPTS_BOOTLOADER_IMAGE) \
		$(FACTORY_SCRIPTS_FASTBOOT_IMAGE) \
                $(FACTORY_SCRIPTS_FASTBOOT_USB) \
		$(INTERNAL_UPDATE_PACKAGE_TARGET) \
		$(DISTTOOLS) $(SELINUX_DEPENDS) \
		$(BOARD_SFU_UPDATE) \
		$(BOARD_GPT_INI) \
		$(factory_scripts_mbr_boot_block) \

	@echo "Package: $@"
	# Generate Package
	$(hide) ./device/intel/build/generate_factory_images \
		--product $(TARGET_PRODUCT) --release $(BUILD_ID) \
		--bootloader $(FACTORY_SCRIPTS_BOOTLOADER_IMAGE) \
		--fastboot $(FACTORY_SCRIPTS_FASTBOOT_IMAGE) \
		--update-archive $(INTERNAL_UPDATE_PACKAGE_TARGET) \
		$(FACTORY_SCRIPTS_OEMVARS) \
		--gpt $(BOARD_GPT_INI) \
		$(factory_scripts_mbr_boot_block_option) \
		--unlock --erase \
		--sleeptime 45 \
		--input $(FACTORY_SCRIPTS_FASTBOOT_USB)=fastboot-usb.img \
		$(patsubst %,--sfu-capsule %,$(BOARD_SFU_UPDATE)) \
		--output $@

.PHONY: factoryscripts
factoryscripts: $(FACTORY_SCRIPTS_PACKAGE_TARGET)

ifeq ($(TARGET_BUILD_INTEL_FACTORY_SCRIPTS),true)
$(call dist-for-goals,droidcore,$(FACTORY_SCRIPTS_PACKAGE_TARGET))
endif

