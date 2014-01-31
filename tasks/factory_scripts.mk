# -----------------------------------------------------------------
# Factory Scripts

BUILD_ID_LC := $(shell echo $(BUILD_ID) | tr A-Z a-z)
FACTORY_SCRIPTS_PACKAGE_TARGET := $(PRODUCT_OUT)/$(TARGET_PRODUCT)-$(BUILD_ID_LC)-factory.tgz
intermediates := $(call intermediates-dir-for,PACKAGING,factory_scripts)
FACTORY_SCRIPTS_BOOTLOADER_IMAGE := $(intermediates)/bootloader-$(TARGET_PRODUCT)-$(FILE_NAME_TAG).bin
FACTORY_SCRIPTS_FASTBOOT_IMAGE := $(intermediates)/fastboot-$(TARGET_PRODUCT)-$(FILE_NAME_TAG).img

$(FACTORY_SCRIPTS_BOOTLOADER_IMAGE): $(BUILT_TARGET_FILES_PACKAGE)
	# Create Intermediates
	mkdir -p $(intermediates)
	# Generate Boot Image
	$(hide) ./device/intel/build/boot_efi_from_target_files.py --partition RADIO $(BUILT_TARGET_FILES_PACKAGE) $(FACTORY_SCRIPTS_BOOTLOADER_IMAGE)

$(FACTORY_SCRIPTS_FASTBOOT_IMAGE): $(BUILT_TARGET_FILES_PACKAGE)
	# Create Intermediates
	mkdir -p $(intermediates)
	# Generate EFI Image
	$(hide) ./device/intel/build/boot_img_from_target_files.py --partition FASTBOOT $(BUILT_TARGET_FILES_PACKAGE) $(FACTORY_SCRIPTS_FASTBOOT_IMAGE)

$(FACTORY_SCRIPTS_PACKAGE_TARGET): $(FACTORY_SCRIPTS_BOOTLOADER_IMAGE) $(FACTORY_SCRIPTS_FASTBOOT_IMAGE) $(INTERNAL_UPDATE_PACKAGE_TARGET) $(DISTTOOLS) $(SELINUX_DEPENDS)
	@echo "Package: $@"
	@echo ----- Making factory scripts ------
	# Generate Package
	$(hide) ./device/intel/build/releasetools/generate_factory_images.py --product $(TARGET_PRODUCT) --release $(BUILD_ID) --bootloader $(FACTORY_SCRIPTS_BOOTLOADER_IMAGE) --fastboot $(FACTORY_SCRIPTS_FASTBOOT_IMAGE) --update-archive $(INTERNAL_UPDATE_PACKAGE_TARGET) --fastboot-args '-t 192.168.42.1' --sleeptime 20 --no-checksum --output $(PRODUCT_OUT)
	@echo ----- Made factory scripts --------

.PHONY: factoryscripts
factoryscripts: $(FACTORY_SCRIPTS_PACKAGE_TARGET)
