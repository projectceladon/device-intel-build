name := $(TARGET_PRODUCT)
ifeq ($(TARGET_BUILD_TYPE),debug)
  name := $(name)_debug
endif
name := $(name)-flashfiles-$(FILE_NAME_TAG)


ifeq ($(USE_INTEL_FLASHFILES),true)
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

else # FLASHFILE_VARIANTS
INTEL_FACTORY_FLASHFILES_TARGET := $(PRODUCT_OUT)/$(name).zip

$(INTEL_FACTORY_FLASHFILES_TARGET): $(BUILT_TARGET_FILES_PACKAGE) $(fftf) $(MKDOSFS) $(MCOPY)
	$(hide) mkdir -p $(dir $@)
	$(hide) $(fftf) $(BUILT_TARGET_FILES_PACKAGE) $@

$(call dist-for-goals,droidcore,$(INTEL_FACTORY_FLASHFILES_TARGET))
endif # FLASHFILE_VARIANTS

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

endif # USE_INTEL_FLASHFILES

# FIXME: We need to extend flashfiles_from_target_files so that it can
# create flashfiles instead of this completely different logic which doesn't
# support the creation of production-signed flashfiles
ifeq ($(USE_SOFIA_FLASHFILES),true)

INTEL_FACTORY_FLASHFILES_TARGET := $(PRODUCT_OUT)/$(name).zip

# FIXME: Shouldn't hard-code a particular product directory, either move
# to device/intel/common or make it something set by a BoardConfig.mk var.
# The scripts should be in a common location as well, although the hope is
# that they will instead be superseded by flashfiles_from_target_files
FLS_FLASHFILES_CONFIG ?= device/intel/sofia3gr/support/fls_flashfiles.json
FLASHFILES_JSON := $(PRODUCT_OUT)/fls/fls/flash.json
$(eval FLS_FLASHFILES_T2F := $(shell ./device/intel/sofia3gr/support/flashdep.py $(FLS_FLASHFILES_CONFIG)))
FLASHFILES_DEPS := $(foreach item,$(FLS_FLASHFILES_T2F),$(call word-colon,2,$(item)))

$(FLASHFILES_JSON): $(FLS_FLASHFILES_CONFIG) $(FLASHFILES_DEPS)
	$(hide) mkdir -p $(@D)
	$(hide) ./device/intel/sofia3gr/support/flashxml.py -c $< \
			-p $(TARGET_PRODUCT) -b $(BUILD_NUMBER) \
			-d $(@D) -t "$(FLS_FLASHFILES_T2F)"

$(INTEL_FACTORY_FLASHFILES_TARGET): $(FLASHFILES_DEPS) $(FLASHFILES_JSON)
	$(hide) rm -rf $@
	$(hide) zip -j $@ $(FLASHFILES_DEPS) $(FLASHFILES_JSON)

$(call dist-for-goals,droidcore,$(INTEL_FACTORY_FLASHFILES_TARGET))
endif # USE_SOFIA_FLASHFILES

.PHONY: flashfiles
flashfiles: $(INTEL_FACTORY_FLASHFILES_TARGET)

ifeq ($(USE_INTEL_FLASHFILES),false)
publish_ifwi:
	@echo "Warning: Unable to fulfill publish_ifwi makefile request"
endif
