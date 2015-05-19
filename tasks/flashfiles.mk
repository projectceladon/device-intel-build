ifeq ($(USE_INTEL_FLASHFILES),true)

name := $(TARGET_PRODUCT)
ifeq ($(TARGET_BUILD_TYPE),debug)
  name := $(name)_debug
endif
name := $(name)-flashfiles-$(FILE_NAME_TAG)
fftf := device/intel/build/releasetools/flashfiles_from_target_files
odf := device/intel/build/releasetools/ota_deployment_fixup

ifneq ($(FLASHFILE_VARIANTS),)
INTEL_FACTORY_FLASHFILES_TARGET :=
$(foreach var,$(FLASHFILE_VARIANTS), \
	$(info Adding $(var)) \
	$(eval fn_prefix := $(OUT)/$(TARGET_PRODUCT)) \
	$(eval fn_suffix := $(var)-$(FILE_NAME_TAG)) \
	$(eval ff_zip := $(fn_prefix)-flashfiles-$(fn_suffix).zip) \
	$(eval ota_zip := $(fn_prefix)-ota-$(fn_suffix).zip) \
	$(eval INTEL_FACTORY_FLASHFILES_TARGET += $(ff_zip)) \
	$(eval INTEL_OTA_PACKAGES += $(ota_zip)) \
	$(call dist-for-goals,droidcore,$(ff_zip):$(notdir $(ff_zip))) \
	$(call dist-for-goals,droidcore,$(ota_zip):$(notdir $(ota_zip))))

$(INTEL_FACTORY_FLASHFILES_TARGET): $(BUILT_TARGET_FILES_PACKAGE) $(fftf) $(MKDOSFS) $(MCOPY)
	$(hide) mkdir -p $(dir $@)
	$(eval y = $(subst -, ,$(basename $(@F))))
	$(eval DEV = $(word 3, $(y)))
	$(hide) $(fftf) --variant=$(DEV) $(BUILT_TARGET_FILES_PACKAGE) $@

$(INTEL_OTA_PACKAGES): $(INTERNAL_OTA_PACKAGE_TARGET) $(BUILT_TARGET_FILES_PACKAGE) $(odf) $(DISTTOOLS)
	$(hide) mkdir -p $(dir $@)
	$(eval y = $(subst -, ,$(basename $(@F))))
	$(eval DEV = $(word 3, $(y)))
	$(hide) $(odf) --verbose --variant=$(DEV) \
		--target_files $(BUILT_TARGET_FILES_PACKAGE) \
		$(INTERNAL_OTA_PACKAGE_TARGET) $@

otapackage: $(INTEL_OTA_PACKAGES)

else
INTEL_FACTORY_FLASHFILES_TARGET := $(PRODUCT_OUT)/$(name).zip

$(INTEL_FACTORY_FLASHFILES_TARGET): $(BUILT_TARGET_FILES_PACKAGE) $(fftf) $(MKDOSFS) $(MCOPY)
	$(hide) mkdir -p $(dir $@)
	$(hide) $(fftf) $(BUILT_TARGET_FILES_PACKAGE) $@

$(call dist-for-goals,droidcore,$(INTEL_FACTORY_FLASHFILES_TARGET))
endif

.PHONY: flashfiles
flashfiles: $(INTEL_FACTORY_FLASHFILES_TARGET)
else
ifeq ($(USE_INTEL_FLASHFILES),sofia)
#for sofia
.PHONY: flashfiles
flashfiles: droid

.PHONY: blank_flashfiles
blank_flashfiles:
include device/intel/sofia3gr/flashfiles.mk
endif
endif
