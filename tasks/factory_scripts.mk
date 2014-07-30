# -----------------------------------------------------------------
# Factory Scripts

# FIXME why the conversion to lowercase??
BUILD_ID_LC := $(shell echo $(BUILD_ID) | tr A-Z a-z)
FACTORY_SCRIPTS_PACKAGE_TARGET := $(PRODUCT_OUT)/$(TARGET_PRODUCT)-$(BUILD_ID_LC)-factory.tgz
FACTORY_SCRIPTS_OEMVARS := $(if $(BOARD_OEM_VARS_FILE),--oemvars $(BOARD_OEM_VARS_FILE))

# For legacy boot, we need to include the MBR boot block
ifeq ($(TARGET_USE_SYSLINUX),true)
	factory_scripts_mbr_boot_block = $(BOARD_MBR_BLOCK_BIN)
	factory_scripts_mbr_boot_block_option = --mbr $(BOARD_MBR_BLOCK_BIN)
else
	factory_scripts_mbr_boot_block :=
	factory_scripts_mbr_boot_block_option :=
endif


$(FACTORY_SCRIPTS_PACKAGE_TARGET): \
		device/intel/build/generate_factory_images \
		$(PRODUCT_OUT)/bootloader \
		$(PRODUCT_OUT)/fastboot.img \
		$(PRODUCT_OUT)/fastboot-usb.img \
		$(INTERNAL_UPDATE_PACKAGE_TARGET) \
		$(DISTTOOLS) $(SELINUX_DEPENDS) \
		$(BOARD_SFU_UPDATE) \
		$(BOARD_GPT_INI) \
		$(factory_scripts_mbr_boot_block) \

	@echo "Package: $@"
	# Generate Package
	$(hide) ./device/intel/build/generate_factory_images \
		--product $(TARGET_PRODUCT) --release $(BUILD_ID) \
		--bootloader $(PRODUCT_OUT)/bootloader \
		--fastboot $(PRODUCT_OUT)/fastboot.img \
		--update-archive $(INTERNAL_UPDATE_PACKAGE_TARGET) \
		$(FACTORY_SCRIPTS_OEMVARS) \
		--gpt $(BOARD_GPT_INI) \
		$(factory_scripts_mbr_boot_block_option) \
		--unlock --erase \
		--sleeptime 45 \
		--input $(PRODUCT_OUT)/fastboot-usb.img=fastboot-usb.img \
		$(patsubst %,--sfu-capsule %,$(BOARD_SFU_UPDATE)) \
		--output $@

.PHONY: factoryscripts
factoryscripts: $(FACTORY_SCRIPTS_PACKAGE_TARGET)

ifeq ($(TARGET_BUILD_INTEL_FACTORY_SCRIPTS),true)
$(call dist-for-goals,droidcore,$(FACTORY_SCRIPTS_PACKAGE_TARGET))
endif

