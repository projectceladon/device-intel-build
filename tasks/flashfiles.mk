name := $(TARGET_PRODUCT)
ifneq ($(findstring acrn,$(TARGET_PRODUCT)),)
name := $(TARGET_PRODUCT)-guest
endif
ifeq ($(TARGET_BUILD_TYPE),debug)
  name := $(name)_debug
endif
ifeq ($(RELEASE_BUILD),true)
flash_name := $(name)-sign-flashfiles-$(FILE_NAME_TAG)
target_name := $(name)-sign-targetfile-$(FILE_NAME_TAG)
gpt_name := $(PRODUCT_OUT)/release_sign/$(name).img
endif
name := $(name)-flashfiles-$(FILE_NAME_TAG)
BUILDNUM := $(shell $(DATE) +%H%M%3S)
ifeq ($(RELEASE_BUILD),true)
BUILT_RELEASE_FLASH_FILES_PACKAGE := $(PRODUCT_OUT)/$(flash_name).zip
BUILT_RELEASE_TARGET_FILES_PACKAGE := $(PRODUCT_OUT)/$(target_name).zip
ifeq ($(SUPER_IMG_IN_FLASHZIP),true)
BUILT_RELEASE_SUPER_IMAGE := $(PRODUCT_OUT)/release_sign/super.img
endif
SOONG_HOST_TOOL := \
	PATH="$(SOONG_HOST_OUT)/bin:$$PATH"

APEX_LIST := com.android.tethering.apex,\
			 com.android.media.swcodec.apex,\
			 com.android.ondevicepersonalization.apex,\
			 com.android.scheduling.apex,\
			 com.android.media.apex,\
			 com.android.conscrypt.apex,\
			 com.android.resolv.apex,\
			 com.android.tzdata.apex,\
			 com.android.btservices.apex,\
			 com.android.sdkext.apex,\
			 com.android.runtime.apex,\
			 com.android.i18n.apex
BUILT_APEXS := $(subst $(space),,$(APEX_LIST))

$(BUILT_RELEASE_TARGET_FILES_PACKAGE):$(BUILT_TARGET_FILES_PACKAGE)
	@echo "Package release: $@"
	$(SOONG_HOST_TOOL) \
	$(HOST_OUT_EXECUTABLES)/sign_target_files_apks -o \
	-d device/intel/build/testkeys/cts-release-test \
	--key_mapping  build/target/product/security/networkstack=device/intel/build/testkeys/cts-release-test/networkstack \
	--extra_apks             $(BUILT_APEXS)=device/intel/build/testkeys/cts-release-test/apex \
	--extra_apex_payload_key $(BUILT_APEXS)=device/intel/build/testkeys/cts-release-test/apex.pem \
	$(BUILT_TARGET_FILES_PACKAGE) $@

ifeq ($(SUPER_IMG_IN_FLASHZIP),true)
$(BUILT_RELEASE_SUPER_IMAGE):$(BUILT_RELEASE_TARGET_FILES_PACKAGE)
	mkdir -p $(PRODUCT_OUT)/release_sign
	build/make/tools/releasetools/build_super_image.py -v $< $@

GPT_DIR := $(PRODUCT_OUT)/ff_temp
tos_image := $(GPT_DIR)/tos.img
ifeq ($(tos_bin),none)
tos_image := none
endif

ifeq ($(BUILD_GPTIMAGE), true)
$(gpt_name):$(BUILT_RELEASE_FLASH_FILES_PACKAGE)
	rm -rf $(GPT_DIR)
	mkdir -p $(GPT_DIR)
	unzip $< -d $(GPT_DIR)
	$(SIMG2IMG) $(GPT_DIR)/super.img $(GPT_DIR)/super.img.raw
	$(SIMG2IMG) $(GPT_DIR)/config.img $(GPT_DIR)/config.img.raw

	$(INTEL_PATH_BUILD)/create_gpt_image.py \
		--create $@ \
		--block $(BOARD_FLASH_BLOCK_SIZE) \
		--table $(BOARD_GPT_INI) \
		--size $(gptimage_size) \
		--bootloader $(GPT_DIR)/bootloader.img \
		--tos $(tos_image) \
		--boot $(GPT_DIR)/boot.img \
		--vbmeta $(GPT_DIR)/vbmeta.img \
		--super $(GPT_DIR)/super.img.raw \
		--acpio  $(GPT_DIR)/acpio.img \
		--vendor_boot $(GPT_DIR)/vendor_boot.img \
		--config $(GPT_DIR)/config.img.raw
	$(hide) rm -f $@.gz
	$(hide) gzip -f $@
	$(hide) rm -rf $(GPT_DIR)
else
$(gpt_name):
	@echo "skip build gptimages"
endif

$(BUILT_RELEASE_FLASH_FILES_PACKAGE):$(BUILT_RELEASE_SUPER_IMAGE) $(legacy_fftf) $(UEFI_ADDITIONAL_TOOLS)
	$(hide) mkdir -p $(dir $@)
	$(legacy_fftf) $(FLASHFILES_ADD_ARGS) --mv_config_default=$(notdir $(mvcfg_default_arg)) --add_image=$(BUILT_RELEASE_SUPER_IMAGE) $(BUILT_RELEASE_TARGET_FILES_PACKAGE) $@
	#remove system.img vendor.img product.img from flashfiles.zip
	$(hide)zip -d $@ "system.img" "product.img" "vendor.img";
else
$(BUILT_RELEASE_FLASH_FILES_PACKAGE):$(BUILT_RELEASE_TARGET_FILES_PACKAGE) $(legacy_fftf) $(UEFI_ADDITIONAL_TOOLS)
	$(hide) mkdir -p $(dir $@)
	$(legacy_fftf) $(FLASHFILES_ADD_ARGS) --mv_config_default=$(notdir $(mvcfg_default_arg)) $(BUILT_RELEASE_TARGET_FILES_PACKAGE) $@
endif
endif

ifeq ($(USE_INTEL_FLASHFILES),true)
fftf := $(INTEL_PATH_BUILD)/releasetools/flashfiles_from_target_files.sh
legacy_fftf := $(INTEL_PATH_BUILD)/releasetools/flashfiles_from_target_files
odf := $(INTEL_PATH_BUILD)/releasetools/ota_deployment_fixup

ifeq ($(use_tar),true)
    fn_compress_format := tar.gz
else
    fn_compress_format := zip
endif

ifneq ($(FLASHFILE_VARIANTS),)
  # Generate variant specific flashfiles if VARIANT_SPECIFIC_FLASHFILES is True
  ifeq ($(VARIANT_SPECIFIC_FLASHFILES),true)
    INTEL_FACTORY_FLASHFILES_TARGET :=
      $(foreach var,$(FLASHFILE_VARIANTS), \
	    $(info Adding $(var)) \
	    $(eval fn_prefix := $(PRODUCT_OUT)/$(TARGET_PRODUCT)) \
	    $(eval fn_suffix := $(var)-$(FILE_NAME_TAG)) \
	    $(eval ff_zip := $(fn_prefix)-flashfiles-$(fn_suffix).$(fn_compress_format)) \
	    $(eval INTEL_FACTORY_FLASHFILES_TARGET += $(ff_zip)) \
	    $(call dist-for-goals,droidcore,$(ff_zip):$(notdir $(ff_zip))))

	  $(INTEL_FACTORY_FLASHFILES_TARGET): $(BUILT_TARGET_FILES_PACKAGE) $(fftf) $(legacy_fftf) $(UEFI_ADDITIONAL_TOOLS)
	  $(hide) mkdir -p $(dir $@)
	  $(eval y = $(subst -, ,$(basename $(@F))))
	  $(eval DEV = $(word 3, $(y)))
	  $(eval mvcfg_dev = $(MV_CONFIG_DEFAULT_TYPE.$(DEV)))
	  $(if $(mvcfg_dev), $(eval mvcfg_default_arg = $(mvcfg_dev)),$(eval mvcfg_default_arg = $(MV_CONFIG_DEFAULT_TYPE)))
	  $(hide) $(legacy_fftf) --variant=$(DEV) --mv_config_default=$(notdir $(mvcfg_default_arg)) $(BUILT_TARGET_FILES_PACKAGE) $@
  endif

ifneq ($(TARGET_SKIP_OTA_PACKAGE), true)
  # Generate OTA fixup files
  INTEL_OTA_PACKAGES :=
  $(foreach var,$(OTA_VARIANTS), \
	$(info Adding $(var)) \
	$(eval fn_prefix := $(PRODUCT_OUT)/$(TARGET_PRODUCT)) \
	$(eval fn_suffix := $(var)-$(FILE_NAME_TAG)) \
	$(eval ota_zip := $(fn_prefix)-ota-$(fn_suffix).zip) \
	$(eval INTEL_OTA_PACKAGES += $(ota_zip)) \
	$(call dist-for-goals,droidcore,$(ota_zip):$(notdir $(ota_zip))))

  $(INTEL_OTA_PACKAGES): $(INTERNAL_OTA_PACKAGE_TARGET) $(BUILT_TARGET_FILES_PACKAGE) $(odf) $(DISTTOOLS)
	$(hide) mkdir -p $(dir $@)
	$(eval y = $(subst -, ,$(basename $(@F))))
	$(eval DEV = $(word 3, $(y)))
	$(hide) export ANDROID_BUILD_TOP=$(PWD); $(odf) --verbose --buildnum=$(BUILDNUM) --variant=$(DEV) \
		--target_files $(BUILT_TARGET_FILES_PACKAGE) \
		$(INTERNAL_OTA_PACKAGE_TARGET) $@

  otapackage: $(INTEL_OTA_PACKAGES)
endif

endif # Generate variant-specific files

#Flag for unified flashfile when variants exist
ifneq ($(FLASHFILE_VARIANTS),)
FLASHFILES_ADD_ARGS := '--unified-variants'
endif

ifeq ($(use_tar),true)
    INTEL_FACTORY_FLASHFILES_TARGET := $(PRODUCT_OUT)/$(name).tar.gz
else
    INTEL_FACTORY_FLASHFILES_TARGET := $(PRODUCT_OUT)/$(name).zip
endif

ifneq ($(SOFIA_FIRMWARE_VARIANTS),)
mvcfg_default_arg = $(MV_CONFIG_DEFAULT_TYPE.$(firstword $(SOFIA_FIRMWARE_VARIANTS)))
else
mvcfg_default_arg = $(MV_CONFIG_DEFAULT_TYPE)
endif

ifeq ($(SUPER_IMG_IN_FLASHZIP),true)
$(INTEL_FACTORY_FLASHFILES_TARGET): $(BUILT_TARGET_FILES_PACKAGE) $(fftf) $(legacy_fftf) $(UEFI_ADDITIONAL_TOOLS) $(INTERNAL_SUPERIMAGE_DIST_TARGET)
	$(hide) mkdir -p $(dir $@)
ifeq ($(use_tar),true)
	$(fftf) $@
else
	$(legacy_fftf) $(FLASHFILES_ADD_ARGS) --mv_config_default=$(notdir $(mvcfg_default_arg)) --add_image=$(INTERNAL_SUPERIMAGE_DIST_TARGET) $(BUILT_TARGET_FILES_PACKAGE) $@
	#remove system.img vendor.img product.img from flashfiles.zip
	$(hide)zip -d $@ "system.img" "product.img" "vendor.img";
endif
else
$(INTEL_FACTORY_FLASHFILES_TARGET): $(BUILT_TARGET_FILES_PACKAGE) $(legacy_fftf) $(UEFI_ADDITIONAL_TOOLS)
	$(hide) mkdir -p $(dir $@)
	$(legacy_fftf) $(FLASHFILES_ADD_ARGS) --mv_config_default=$(notdir $(mvcfg_default_arg)) $(BUILT_TARGET_FILES_PACKAGE) $@
endif

ifeq ($(PUBLISH_CMCC_IMG),true)
CMCC_TARGET := $(PRODUCT_OUT)/$(subst -flashfiles-,-cmcc-,$(name)).zip
CMCC_IMG_PATH := $(PRODUCT_OUT)/fls/fls/CMCC

$(CMCC_TARGET): droidcore
	$(hide) mkdir -p $(dir $@)
	$(hide) zip -j $@ $(CMCC_IMG_PATH)/*
endif

ifneq ($(FAST_FLASHFILES),false)
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
    $(INSTALLED_VBMETAIMAGE_TARGET) \

fast_flashfiles: $(fftf) $(legacy_fftf) $(UEFI_ADDITIONAL_TOOLS) $(FAST_FLASHFILES_DEPS) | $(ACP)
	$(hide) rm -rf $(FAST_FLASHFILES_DIR)
	$(hide) mkdir -p $(FAST_FLASHFILES_DIR)
	$(legacy_fftf) $(FLASHFILES_ADD_ARGS) --mv_config_default=$(notdir $(mvcfg_default_arg)) --fast $(PRODUCT_OUT) $(FAST_FLASHFILES_DIR)

# add dependencies
droid: fast_flashfiles
flashfiles: fast_flashfiles
else
droid: $(INSTALLED_RADIOIMAGE_TARGET)
endif #FAST_FLASHFILES

ifeq ($(RELEASE_BUILD),true)
$(call dist-for-goals,droidcore,$(BUILT_RELEASE_FLASH_FILES_PACKAGE))
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

IFWI_LIST := EFI_IFWI_BIN IFWI_RVP_BIN IFWI_2GB_BIN IFWI_D0_BIN IFWI_D0_2GB_BIN EFI_AFU_BIN AFU_2GB_BIN AFU_D0_2GB_BIN AFU_D0_BIN BOARD_SFU_UPDATE CAPSULE_2GB EFI_EMMC_BIN

PUB_EFI_IFWI_BIN     := dediprog
PUB_IFWI_RVP_BIN     := dediprog
PUB_IFWI_2GB_BIN     := dediprog
PUB_IFWI_D0_2GB_BIN  := dediprog
PUB_IFWI_D0_BIN      := dediprog
PUB_EFI_AFU_BIN      := afu
PUB_AFU_2GB_BIN      := afu
PUB_AFU_D0_2GB_BIN   := afu
PUB_AFU_D0_BIN       := afu
PUB_BOARD_SFU_UPDATE := capsule
PUB_CAPSULE_2GB      := capsule
PUB_EFI_EMMC_BIN     := stage2

$(foreach ifwi,$(IFWI_LIST),$(eval $(call ifwi_target,$(ifwi),$(PUB_$(ifwi)))))

else
publish_ifwi:
	@echo "Info: board has no ifwi to publish"
endif # BOARD_HAS_NO_IFWI

endif # USE_INTEL_FLASHFILES

# Publish the vertical patches to vertical release tar ball
.PHONY: publish_vertical
publish_vertical:
ifneq (,$(wildcard vendor/intel/utils_vertical))
publish_vertical:
	@echo "Identified Vertical repo and copy the patches to the tar ball"
	$(hide) mkdir -p $(publish_dest)
	$(hide) rm -rf $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
	$(hide) mkdir -p $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
	$(hide) cp -r vendor/intel/utils_vertical $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
	$(hide) mv $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files/utils_vertical $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files/vertical_patches
ifneq (,$(wildcard vendor/intel/fw/keybox_provisioning))
	$(hide) cp -r vendor/intel/fw/keybox_provisioning $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
	$(hide) mv $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files/keybox_provisioning $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files/vertical_keybox_provisioning
endif

else
publish_vertical:
	$(hide) rm -rf $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
endif

ifeq ($(RELEASE_BUILD),true)
ISO_INSTALL_IMG = $(PRODUCT_OUT)/$(TARGET_PRODUCT)-sign-flashfile-$(FILE_NAME_TAG).iso
else
ISO_INSTALL_IMG = $(PRODUCT_OUT)/$(TARGET_PRODUCT)-flashfile-$(FILE_NAME_TAG).iso
endif
ifeq ($(use_tar),true)
ISO_INSTALL_IMG_COMP = $(ISO_INSTALL_IMG).tar.gz
else
ISO_INSTALL_IMG_COMP = $(ISO_INSTALL_IMG).zip
endif
ISO_RELEASE_TAR = $(PRODUCT_OUT)/$(TARGET_PRODUCT)-releasefile-$(TARGET_BUILD_VARIANT).iso.tar.gz
ISO_EFI = $(PRODUCT_OUT)/iso_tmp.efi
iso_basename = $(shell basename $(ISO_INSTALL_IMG))
iso_path = $(shell dirname $(ISO_INSTALL_IMG))

LOCAL_TOOL:= \
   PATH="/bin:$$PATH"

.PHONY: flashfiles
ifeq ($(RELEASE_BUILD),true)
flashfiles: $(INTEL_FACTORY_FLASHFILES_TARGET) $(BUILT_RELEASE_FLASH_FILES_PACKAGE) $(gpt_name) publish_mkdir_dest publish_vertical host-pkg sepolicy_freeze_test check-vintf-all
	@$(ACP) $(BUILT_RELEASE_FLASH_FILES_PACKAGE) $(publish_dest)
ifeq (,$(filter  base_aaos aaos_iasw,$(TARGET_PRODUCT)))
	@echo "Publishing Release files started ..."
	$(hide) mkdir -p $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
	$(hide) cp -r $(PRODUCT_OUT)/*-flashfiles-*.$(fn_compress_format) $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
	$(hide) cp -r $(PRODUCT_OUT)/scripts $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
	$(hide) cp -r vendor/intel/utils/host $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
	$(hide) mv $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files/host $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files/patches
	$(hide) cp -r $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files/* $(TOP)
ifneq (,$(wildcard vendor/intel/utils_vertical))
ifneq (,$(wildcard vendor/intel/fw/keybox_provisioning))
	@echo "vertical_keybox_provisioning included"
	$(hide) tar --exclude=*.git -czf $(TARGET_PRODUCT)-releasefiles-$(TARGET_BUILD_VARIANT).tar.gz scripts *patches $(TARGET_PRODUCT)-flashfiles-*.$(fn_compress_format) *provisioning
else 
	$(hide) tar --exclude=*.git -czf $(TARGET_PRODUCT)-releasefiles-$(TARGET_BUILD_VARIANT).tar.gz scripts *patches $(TARGET_PRODUCT)-flashfiles-*.$(fn_compress_format)
endif
else
	$(hide) tar --exclude=*.git -czf $(TARGET_PRODUCT)-releasefiles-$(TARGET_BUILD_VARIANT).tar.gz scripts *patches $(TARGET_PRODUCT)-flashfiles-*.$(fn_compress_format)
endif 	
	$(hide) cp -r $(TOP)/$(TARGET_PRODUCT)-releasefiles-$(TARGET_BUILD_VARIANT).tar.gz $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)
	$(hide) cp -r $(TOP)/$(TARGET_PRODUCT)-releasefiles-$(TARGET_BUILD_VARIANT).tar.gz $(PRODUCT_OUT)
	@echo "Release files are published"
endif
ifneq (,$(filter caas,$(TARGET_PRODUCT)))
ifneq (,$(wildcard out/dist))
	@echo "Publish the CaaS image as debian_package"
	$(hide)rm -rf $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/
	$(hide)rm -rf $(PRODUCT_OUT)/RELEASE
	$(hide)mkdir -p $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/Release_Deb
ifeq ($(BUILD_GPTIMAGE), true)
	$(hide)cp -r $(PRODUCT_OUT)/release_sign/caas*.img.gz $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/Release_Deb
endif
	$(hide)mkdir -p $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/DEBIAN
	$(hide)cp -r device/intel/mixins/groups/device-specific/caas/addon/debian/* $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/DEBIAN/
	$(hide)cp -r $(PRODUCT_OUT)/scripts $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/Release_Deb
	$(hide)cp -r $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/ $(PRODUCT_OUT)
	$(hide)(cd $(PRODUCT_OUT) && $(LOCAL_TOOL) dpkg-deb --build Release/)
	$(hide) cp -r $(PRODUCT_OUT)/*.deb $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)
else
	$(hide)rm -rf  $(PRODUCT_OUT)/*.deb
	$(hide)rm -rf  $(PRODUCT_OUT)/Release
	$(hide)rm -rf $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release
endif
else
	$(hide)rm -rf  $(PRODUCT_OUT)/*.deb
	$(hide)rm -rf  $(PRODUCT_OUT)/Release
	$(hide)rm -rf $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release
endif
else
flashfiles: $(INTEL_FACTORY_FLASHFILES_TARGET) publish_gptimage_var publish_mkdir_dest publish_vertical host-pkg sepolicy_freeze_test check-vintf-all
ifeq (,$(filter  base_aaos aaos_iasw,$(TARGET_PRODUCT)))
	@echo "Publishing Release files started"
	$(hide) mkdir -p $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
	$(hide) cp -r $(PRODUCT_OUT)/*-flashfiles-*.$(fn_compress_format) $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
	$(hide) cp -r $(PRODUCT_OUT)/scripts $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
	$(hide) cp -r vendor/intel/utils/host $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files
	$(hide) mv $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files/host $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files/patches
	$(hide) cp -r $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files/* $(TOP)
ifneq (,$(wildcard vendor/intel/utils_vertical))
ifneq (,$(wildcard vendor/intel/fw/keybox_provisioning))
	@echo "vertical_keybox_provisioning included"
	$(hide) tar  --exclude=*.git -cvf - scripts *patches $(TARGET_PRODUCT)-flashfiles-*.$(fn_compress_format) *provisioning | /usr/bin/pigz > $(TARGET_PRODUCT)-releasefiles-$(TARGET_BUILD_VARIANT).tar.gz
else
	$(hide) tar  --exclude=*.git -cvf - scripts *patches $(TARGET_PRODUCT)-flashfiles-*.$(fn_compress_format) | /usr/bin/pigz > $(TARGET_PRODUCT)-releasefiles-$(TARGET_BUILD_VARIANT).tar.gz
endif
else
	$(hide) tar  --exclude=*.git -cvf - scripts *patches $(TARGET_PRODUCT)-flashfiles-*.$(fn_compress_format) | /usr/bin/pigz > $(TARGET_PRODUCT)-releasefiles-$(TARGET_BUILD_VARIANT).tar.gz
endif
	$(hide) cp -r $(TOP)/$(TARGET_PRODUCT)-releasefiles-$(TARGET_BUILD_VARIANT).tar.gz $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)
	$(hide) cp -r $(TOP)/$(TARGET_PRODUCT)-releasefiles-$(TARGET_BUILD_VARIANT).tar.gz $(PRODUCT_OUT)
	@echo "Release files are published"
endif
ifneq (,$(filter caas,$(TARGET_PRODUCT)))
ifneq (,$(wildcard out/dist))
	@echo "Publish the CaaS image as debian package"
	$(hide)rm -rf $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/
	$(hide)rm -rf $(PRODUCT_OUT)/RELEASE
	$(hide)mkdir -p $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/Release_Deb
ifeq ($(BUILD_GPTIMAGE), true)
	$(hide)cp -r $(PRODUCT_OUT)/caas*.img.gz $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/Release_Deb
endif
	$(hide)mkdir -p $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/DEBIAN
	$(hide)cp -r device/intel/mixins/groups/device-specific/caas/addon/debian/* $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/DEBIAN/
	$(hide)cp -r $(PRODUCT_OUT)/scripts $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/Release_Deb
	$(hide)cp -r $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release/ $(PRODUCT_OUT)
	$(hide)(cd $(PRODUCT_OUT) && $(LOCAL_TOOL) dpkg-deb --build Release/)
	$(hide) cp -r $(PRODUCT_OUT)/*.deb $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)
else
	$(hide)rm -rf  $(PRODUCT_OUT)/*.deb
	$(hide)rm -rf  $(PRODUCT_OUT)/Release
	$(hide)rm -rf $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release
endif
else
	$(hide)rm -rf  $(PRODUCT_OUT)/*.deb
	$(hide)rm -rf  $(PRODUCT_OUT)/Release
	$(hide)rm -rf $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release
endif
endif
ifeq ($(USE_INTEL_FLASHFILES),false)
publish_ifwi:
	@echo "Warning: Unable to fulfill publish_ifwi makefile request"
endif

ifneq ($(iso_image),false)
	@echo "Generating ISO image $(ISO_INSTALL_IMG) ...";
	$(hide)rm -rf $(PRODUCT_OUT)/efi_images_tmp/;
	$(hide)rm -rf $(ISO_INSTALL_IMG) $(ISO_INSTALL_IMG_COMP)
	$(hide)mkdir -p $(PRODUCT_OUT)/efi_images_tmp;

ifeq ($(use_tar),true)
	cp -r $(PRODUCT_OUT)/$(TARGET_PRODUCT)-flashfiles-*/* $(PRODUCT_OUT)/efi_images_tmp/.
else
ifeq ($(RELEASE_BUILD),true)
	$(hide)unzip $(BUILT_RELEASE_FLASH_FILES_PACKAGE) -d $(PRODUCT_OUT)/efi_images_tmp/ > /dev/null;
else

	$(hide)unzip $(INTEL_FACTORY_FLASHFILES_TARGET) -d $(PRODUCT_OUT)/efi_images_tmp/ > /dev/null;
endif
endif
	G_size=`echo "$$((1 << 32))"`; \
	for img in `ls $(PRODUCT_OUT)/efi_images_tmp/`;do \
		size=`stat -c %s $(PRODUCT_OUT)/efi_images_tmp/$${img}`; \
		if [[ $${size} -gt $${G_size} ]]; then \
			echo "Split $${img} due to its size bigger than 4G"; \
			split --bytes=`expr $${G_size} - 1` --numeric-suffixes $(PRODUCT_OUT)/efi_images_tmp/$${img} $(PRODUCT_OUT)/efi_images_tmp/$${img}.part; \
			rm $(PRODUCT_OUT)/efi_images_tmp/$${img}; \
		fi;\
	done;

	$(hide)rm -rf $(ISO_EFI); \
	flashfile_size=`du -s ${PRODUCT_OUT}/efi_images_tmp/ | awk '{print $$1}'`; \
	flashfile_size=`expr $${flashfile_size} + 102400`; \
	flashfile_size=`expr $${flashfile_size} / 63 + 1 `; \
	flashfile_size=`expr $${flashfile_size} \* 63 `; \
	dd if=/dev/zero of=$(ISO_EFI) bs=1024 count=$${flashfile_size};

	$(hide)mkdosfs -F32 -n EFI $(ISO_EFI);
	$(hide)mmd -i $(ISO_EFI) ::EFI;
	$(hide)mmd -i $(ISO_EFI) ::EFI/BOOT;
	$(hide)mcopy -Q -i $(ISO_EFI) $(PRODUCT_OUT)/efi_images_tmp/installer.efi ::EFI/BOOT/bootx64.efi;
	$(hide)mcopy -Q -i $(ISO_EFI) $(PRODUCT_OUT)/efi_images_tmp/* ::;

	$(hide)rm -rf $(PRODUCT_OUT)/iso
	$(hide)mkdir -p $(PRODUCT_OUT)/iso
	$(hide)xorriso -as mkisofs -iso-level 3  -r -V "Civ ISO" -J -joliet-long  -append_partition 2 0xef $(ISO_EFI) \
	 -partition_cyl_align all -o $(ISO_INSTALL_IMG) $(PRODUCT_OUT)/iso/

	@echo "Compress ISO image $(ISO_INSTALL_IMG_COMP) ..."
ifeq ($(use_tar),true)
	$(hide) tar -cvf - -C $(iso_path) $(iso_basename) | /usr/bin/pigz > $(ISO_INSTALL_IMG_COMP)
else
	$(hide)zip -r -j $(ISO_INSTALL_IMG_COMP) $(ISO_INSTALL_IMG)
endif
ifeq (,$(filter  base_aaos aaos_iasw,$(TARGET_PRODUCT)))
	@echo "Zipping ISO release image $(ISO_RELEASE_TAR) ..."
	$(hide)rm -rf $(ISO_RELEASE_TAR)
	$(hide)cp $(ISO_INSTALL_IMG) $(TOP)/
ifneq (,$(wildcard vendor/intel/utils_vertical))
ifneq (,$(wildcard vendor/intel/fw/keybox_provisioning))
	@echo "vertical_keybox_provisioning included"
ifeq ($(use_tar),true)
	$(hide) tar  --exclude=*.git -cvf - scripts *patches *-flashfile-*.iso *provisioning | /usr/bin/pigz > $(ISO_RELEASE_TAR)
else
	$(hide) tar  --exclude=*.git -czf $(ISO_RELEASE_TAR) scripts *patches *-flashfile-*.iso *provisioning
endif
else
ifeq ($(use_tar),true)
	$(hide) tar  --exclude=*.git -cvf - scripts *patches *-flashfile-*.iso | /usr/bin/pigz > $(ISO_RELEASE_TAR)
else
	$(hide) tar  --exclude=*.git -czf $(ISO_RELEASE_TAR) scripts *patches *-flashfile-*.iso
endif
endif
else
ifeq ($(use_tar),true)
	$(hide) tar  --exclude=*.git -cvf - scripts *patches *-flashfile-*.iso | /usr/bin/pigz > $(ISO_RELEASE_TAR)
else
	$(hide) tar  --exclude=*.git -czf $(ISO_RELEASE_TAR) scripts *patches *-flashfile-*.iso
endif
endif
endif
	@echo "make ISO image done ---"
ifeq (,$(filter  base_aaos aaos_iasw,$(TARGET_PRODUCT)))
	$(hide) cp -r $(ISO_RELEASE_TAR) $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)
endif
	$(hide) cp -r $(ISO_INSTALL_IMG_COMP) $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)

	$(hide)rm -rf $(PRODUCT_OUT)/efi_images_tmp/ $(PRODUCT_OUT)/iso $(ISO_EFI)

	@echo "ISO Release files are published"
endif
	$(hide)rm -rf $(TOP)/$(TARGET_PRODUCT)-releasefiles-$(TARGET_BUILD_VARIANT).tar.gz && rm -rf $(TOP)/Release_Files && rm -rf $(TOP)/$(TARGET_PRODUCT)-flashfiles-*.$(fn_compress_format) && rm -rf $(TOP)/scripts && rm -rf $(TOP)/*patches && rm -rf $(TOP)/*provisioning && rm -rf $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/Release_Files $(TOP)/*-flashfile-*.iso
