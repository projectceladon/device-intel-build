name := $(TARGET_PRODUCT)
ifeq ($(TARGET_BUILD_TYPE),debug)
  name := $(name)_debug
endif
name := $(name)-flashfiles-$(FILE_NAME_TAG)


ifeq ($(USE_INTEL_FLASHFILES),true)
fftf := device/intel/build/releasetools/flashfiles_from_target_files
odf := device/intel/build/releasetools/ota_deployment_fixup

ifneq ($(FLASHFILE_VARIANTS),)
  # Generate variant specific flashfiles if VARIANT_SPECIFIC_FLASHFILES is True
  ifeq ($(VARIANT_SPECIFIC_FLASHFILES),true)
    INTEL_FACTORY_FLASHFILES_TARGET :=
      $(foreach var,$(FLASHFILE_VARIANTS), \
	    $(info Adding $(var)) \
	    $(eval fn_prefix := $(OUT)/$(TARGET_PRODUCT)) \
	    $(eval fn_suffix := $(var)-$(FILE_NAME_TAG)) \
	    $(eval ff_zip := $(fn_prefix)-flashfiles-$(fn_suffix).zip) \
	    $(eval INTEL_FACTORY_FLASHFILES_TARGET += $(ff_zip)) \
	    $(call dist-for-goals,droidcore,$(ff_zip):$(notdir $(ff_zip))))

    $(INTEL_FACTORY_FLASHFILES_TARGET): $(BUILT_TARGET_FILES_PACKAGE) $(fftf) $(MKDOSFS) $(MCOPY)
	  $(hide) mkdir -p $(dir $@)
	  $(eval y = $(subst -, ,$(basename $(@F))))
	  $(eval DEV = $(word 3, $(y)))
	  $(hide) $(fftf) --variant=$(DEV) $(BUILT_TARGET_FILES_PACKAGE) $@
  endif

  # Generate OTA fixup files
  INTEL_OTA_PACKAGES :=
  $(foreach var,$(OTA_VARIANTS), \
	$(info Adding $(var)) \
	$(eval fn_prefix := $(OUT)/$(TARGET_PRODUCT)) \
	$(eval fn_suffix := $(var)-$(FILE_NAME_TAG)) \
	$(eval ota_zip := $(fn_prefix)-ota-$(fn_suffix).zip) \
	$(eval INTEL_OTA_PACKAGES += $(ota_zip)) \
	$(call dist-for-goals,droidcore,$(ota_zip):$(notdir $(ota_zip))))

  $(INTEL_OTA_PACKAGES): $(INTERNAL_OTA_PACKAGE_TARGET) $(BUILT_TARGET_FILES_PACKAGE) $(odf) $(DISTTOOLS)
	$(hide) mkdir -p $(dir $@)
	$(eval y = $(subst -, ,$(basename $(@F))))
	$(eval DEV = $(word 3, $(y)))
	$(hide) $(odf) --verbose --variant=$(DEV) \
		--target_files $(BUILT_TARGET_FILES_PACKAGE) \
		$(INTERNAL_OTA_PACKAGE_TARGET) $@

  otapackage: $(INTEL_OTA_PACKAGES)
endif # Generate variant-specific files

#Flag for unified flashfile when variants exist
ifneq ($(FLASHFILE_VARIANTS),)
FLASHFILES_ADD_ARGS := '--unified-variants'
endif

INTEL_FACTORY_FLASHFILES_TARGET := $(PRODUCT_OUT)/$(name).zip

$(INTEL_FACTORY_FLASHFILES_TARGET): $(BUILT_TARGET_FILES_PACKAGE) $(fftf) $(MKDOSFS) $(MCOPY)
	$(hide) mkdir -p $(dir $@)
	$(hide) $(fftf) $(FLASHFILES_ADD_ARGS) $(BUILT_TARGET_FILES_PACKAGE) $@

ifeq ($(FLASHFILE_VARIANTS),)
# Fast flashfiles is for engineering purpose only
# Should not be used on end-user product
.PHONY: fast_flashfiles

FAST_FLASHFILES_DIR := $(PRODUCT_OUT)/fast_flashfiles

FAST_FLASHFILES_DEPS := \
    $(INSTALLED_BOOTIMAGE_TARGET) \
    $(INSTALLED_RADIOIMAGE_TARGET) \
    $(INSTALLED_RECOVERYIMAGE_TARGET) \
    $(INSTALLED_SYSTEMIMAGE) \
    $(INSTALLED_USERDATAIMAGE_TARGET) \
    $(INSTALLED_CACHEIMAGE_TARGET) \
    $(INSTALLED_VENDORIMAGE_TARGET) \
    $(USERFASTBOOT_BOOTIMAGE) \

fast_flashfiles: $(fftf) $(MKDOSFS) $(MCOPY) $(FAST_FLASHFILES_DEPS) | $(ACP)
	$(hide) rm -rf $(FAST_FLASHFILES_DIR)
	$(hide) mkdir -p $(FAST_FLASHFILES_DIR)
	$(hide) $(fftf) --fast $(PRODUCT_OUT) $(FAST_FLASHFILES_DIR)

# add dependencies
droid: fast_flashfiles
flashfiles: fast_flashfiles

endif

$(call dist-for-goals,droidcore,$(INTEL_FACTORY_FLASHFILES_TARGET))

ifneq ($(BOARD_HAS_NO_IFWI),true)

# $1 is ifwi variable suffix
# $2 is the folder where ifwi are published on buildbot

define ifwi_target

ifneq ($$($(1)),)

PUB_IFWI := pub/$(TARGET_PRODUCT)/IFWI/ifwi_uefi_$(TARGET_PRODUCT)
IFWI_NAME :=$$(addprefix $$(TARGET_BUILD_VARIANT)_,$$(notdir $$(realpath $$($(1)))))

ifneq ($$(IFWI_NAME),)
INTEL_FACTORY_$(1) := $$(PRODUCT_OUT)/$$(IFWI_NAME)
else
INTEL_FACTORY_$(1) := $$(PRODUCT_OUT)/$$(TARGET_PRODUCT)_$(1).bin
endif

$$(INTEL_FACTORY_$(1)): $$($(1)) | $$(ACP)
	$$(hide) $$(ACP) $$< $$@

PUB_$(1) := $$(PUB_IFWI)/$(2)/$$(notdir $$(INTEL_FACTORY_$(1)))

$$(PUB_$(1)): $$(INTEL_FACTORY_$(1))
	mkdir -p $$(@D)
	$$(hide) $$(ACP) $$< $$@

ifwi: $$(INTEL_FACTORY_$(1))

publish_ifwi: $$(PUB_$(1))

endif
endef

.PHONY: ifwi
.PHONY: publish_ifwi

IFWI_LIST := EFI_IFWI_BIN IFWI_RVP_BIN IFWI_2GB_BIN EFI_AFU_BIN AFU_2GB_BIN BOARD_SFU_UPDATE CAPSULE_2GB EFI_EMMC_BIN

PUB_EFI_IFWI_BIN := dediprog
PUB_IFWI_RVP_BIN := dediprog
PUB_IFWI_2GB_BIN := dediprog
PUB_EFI_AFU_BIN  := afu
PUB_AFU_2GB_BIN  := afu
PUB_BOARD_SFU_UPDATE := capsule
PUB_CAPSULE_2GB := capsule
PUB_EFI_EMMC_BIN := stage2

$(foreach ifwi,$(IFWI_LIST),$(eval $(call ifwi_target,$(ifwi),$(PUB_$(ifwi)))))

else
publish_ifwi:
	@echo "Info: board has no ifwi to publish"
endif # BOARD_HAS_NO_IFWI

endif # USE_INTEL_FLASHFILES

.PHONY: flashfiles
flashfiles: $(INTEL_FACTORY_FLASHFILES_TARGET)

ifeq ($(USE_INTEL_FLASHFILES),false)
publish_ifwi:
	@echo "Warning: Unable to fulfill publish_ifwi makefile request"
endif
