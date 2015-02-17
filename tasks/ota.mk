# INTEL_OTATOOLS defined in device/intel/build/core/definitions.mk
# These are here because these INTERNAL_* variables are only defined
# halfway through build/core/Makefile, long after definitions.mk has
# been imported

$(INTERNAL_OTA_PACKAGE_TARGET): $(INTEL_OTATOOLS)
$(INTERNAL_UPDATE_PACKAGE_TARGET): $(INTEL_OTATOOLS)

