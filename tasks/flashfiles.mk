ifeq ($(USE_INTEL_FLASHFILES),true)

name := $(TARGET_PRODUCT)
ifeq ($(TARGET_BUILD_TYPE),debug)
  name := $(name)_debug
endif
name := $(name)-flashfiles-$(FILE_NAME_TAG)

INTEL_FACTORY_FLASHFILES_TARGET := $(PRODUCT_OUT)/$(name).zip
fftf := device/intel/build/releasetools/flashfiles_from_target_files

$(INTEL_FACTORY_FLASHFILES_TARGET): $(BUILT_TARGET_FILES_PACKAGE) $(fftf) $(MKDOSFS) $(MCOPY)
	$(hide) mkdir -p $(dir $@)
	$(hide) $(fftf) $(BUILT_TARGET_FILES_PACKAGE) $@

$(call dist-for-goals,droidcore,$(INTEL_FACTORY_FLASHFILES_TARGET))

.PHONY: flashfiles
flashfiles: $(INTEL_FACTORY_FLASHFILES_TARGET)

endif
