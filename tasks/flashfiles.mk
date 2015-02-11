ifeq ($(USE_INTEL_FLASHFILES),true)

name := $(TARGET_PRODUCT)
ifeq ($(TARGET_BUILD_TYPE),debug)
  name := $(name)_debug
endif
name := $(name)-flashfiles-$(FILE_NAME_TAG)
INTEL_FACTORY_FLASHFILES_TARGET := $(PRODUCT_OUT)/$(name).zip

ifneq ($(FLASHFILE_VARIANTS),)
INTEL_FACTORY_FLASHFILES_TARGET :=
$(foreach var,$(FLASHFILE_VARIANTS), \
	$(info Adding $(var)) \
	$(eval var_zip := $(OUT)/$(TARGET_PRODUCT)-flashfiles-$(var)-$(FILE_NAME_TAG).zip) \
	$(eval INTEL_FACTORY_FLASHFILES_TARGET += $(var_zip)) \
	$(call dist-for-goals,droidcore,$(var_zip):$(TARGET_PRODUCT)-flashfiles-$(var)-$(FILE_NAME_TAG).zip))
else
$(call dist-for-goals,droidcore,$(INTEL_FACTORY_FLASHFILES_TARGET))
endif

fftf := device/intel/build/releasetools/flashfiles_from_target_files

ifneq ($(FLASHFILE_VARIANTS),)
$(INTEL_FACTORY_FLASHFILES_TARGET): $(BUILT_TARGET_FILES_PACKAGE) $(fftf) $(MKDOSFS) $(MCOPY)
	$(hide) mkdir -p $(dir $@)
	$(eval y = $(subst -, ,$(basename $(@F))))
	$(eval DEV = $(word 3, $(y)))
	$(hide) $(fftf) --file-path=$(OUT) --variant=$(DEV) $(BUILT_TARGET_FILES_PACKAGE) $@
else
$(INTEL_FACTORY_FLASHFILES_TARGET): $(BUILT_TARGET_FILES_PACKAGE) $(fftf) $(MKDOSFS) $(MCOPY)
	$(hide) mkdir -p $(dir $@)
	$(hide) $(fftf) $(BUILT_TARGET_FILES_PACKAGE) $@
endif


.PHONY: flashfiles
flashfiles: $(INTEL_FACTORY_FLASHFILES_TARGET)

endif
