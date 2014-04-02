# -----------------------------------------------------------------
# Factory Scripts

BUILD_ID_LC := $(shell echo $(BUILD_ID) | tr A-Z a-z)
FACTORY_SCRIPTS_PACKAGE_TARGET := $(PRODUCT_OUT)/$(TARGET_PRODUCT)-$(BUILD_ID_LC)-factory.tgz
intermediates := $(call intermediates-dir-for,PACKAGING,factory_scripts)
FACTORY_SCRIPTS_BOOTLOADER_IMAGE := $(intermediates)/bootloader-$(TARGET_PRODUCT)-$(FILE_NAME_TAG).bin
FACTORY_SCRIPTS_FASTBOOT_IMAGE := $(intermediates)/fastboot-$(TARGET_PRODUCT)-$(FILE_NAME_TAG).img

# We could just get the fastboot.img and bootloader blobs from the $OUT
# directory, but let's make sure these scripts don't bit-rot as they are
# critical for release workflow.

$(FACTORY_SCRIPTS_BOOTLOADER_IMAGE): $(BUILT_TARGET_FILES_PACKAGE)
	mkdir -p $(dir $@)
	$(hide) ./device/intel/build/releasetools/bootloader_from_target_files \
		$(BUILT_TARGET_FILES_PACKAGE) $@

$(FACTORY_SCRIPTS_FASTBOOT_IMAGE): $(BUILT_TARGET_FILES_PACKAGE)
	mkdir -p $(dir $@)
	$(hide) MKBOOTIMG=$(BOARD_CUSTOM_MKBOOTIMG) \
		./device/intel/build/releasetools/fastboot_from_target_files \
		$(BUILT_TARGET_FILES_PACKAGE) $@

# TODO: add scripts to create fastboot-usb.img from a target-files-package
$(FACTORY_SCRIPTS_PACKAGE_TARGET): \
		$(FACTORY_SCRIPTS_BOOTLOADER_IMAGE) \
		$(FACTORY_SCRIPTS_FASTBOOT_IMAGE) \
		$(INTERNAL_UPDATE_PACKAGE_TARGET) \
		$(DISTTOOLS) $(SELINUX_DEPENDS) \
		$(BOARD_GPT_INI) \
		$(PRODUCT_OUT)/fastboot-usb.img \

	@echo "Package: $@"
	# Generate Package
	$(hide) ./device/intel/build/generate_factory_images \
		--product $(TARGET_PRODUCT) --release $(BUILD_ID) \
		--bootloader $(FACTORY_SCRIPTS_BOOTLOADER_IMAGE) \
		--fastboot $(FACTORY_SCRIPTS_FASTBOOT_IMAGE) \
		--update-archive $(INTERNAL_UPDATE_PACKAGE_TARGET) \
		--gpt $(BOARD_GPT_INI) \
		--unlock --erase \
		--fastboot-args '-t 192.168.42.1' --sleeptime 30 \
		--input $(PRODUCT_OUT)/fastboot-usb.img \
		--no-checksum --output $(PRODUCT_OUT)

.PHONY: factoryscripts
factoryscripts: $(FACTORY_SCRIPTS_PACKAGE_TARGET)

ifeq ($(TARGET_BUILD_INTEL_FACTORY_SCRIPTS),true)
$(call dist-for-goals,droidcore,$(FACTORY_SCRIPTS_PACKAGE_TARGET))
endif

