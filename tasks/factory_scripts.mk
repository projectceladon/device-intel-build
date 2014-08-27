# -----------------------------------------------------------------
# Factory Scripts

# FIXME why the conversion to lowercase??
BUILD_ID_LC := $(shell echo $(BUILD_ID) | tr A-Z a-z)
FACTORY_SCRIPTS_PACKAGE_TARGET := $(PRODUCT_OUT)/$(TARGET_PRODUCT)-$(BUILD_ID_LC)-factory.tgz
FACTORY_SCRIPTS_RADIO := $(if $(BOARD_RADIOIMAGE), --radio $(BOARD_RADIOIMAGE))

$(FACTORY_SCRIPTS_PACKAGE_TARGET): \
		device/intel/build/generate_factory_images \
		$(PRODUCT_OUT)/bootloader \
		$(INTERNAL_UPDATE_PACKAGE_TARGET) \
		$(BOARD_RADIOIMAGE) \
		$(DISTTOOLS) $(SELINUX_DEPENDS) \

	@echo "Package: $@"
	# Generate Package
	$(hide) ./device/intel/build/generate_factory_images \
		--product $(TARGET_PRODUCT) --release $(BUILD_ID) \
		--bootloader $(PRODUCT_OUT)/bootloader \
		--update-archive $(INTERNAL_UPDATE_PACKAGE_TARGET) \
		$(FACTORY_SCRIPTS_RADIO) \
		--sleeptime 45 \
		--output $@

.PHONY: factoryscripts
factoryscripts: $(FACTORY_SCRIPTS_PACKAGE_TARGET)

ifeq ($(TARGET_BUILD_INTEL_FACTORY_SCRIPTS),true)
$(call dist-for-goals,droidcore,$(FACTORY_SCRIPTS_PACKAGE_TARGET))
endif

