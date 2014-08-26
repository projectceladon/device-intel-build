ifeq ($(TARGET_BUILD_INTEL_FACTORY_FLASHFILES),true)

flashfiles_zip := $(OUT)/flashfiles.zip
ff_intermediates := $(call intermediates-dir-for,PACKAGING,flashfiles)

define copy-flashfile
$(hide) $(ACP) $(1) $(2)

endef

$(flashfiles_zip): \
		$(INSTALLED_SYSTEMIMAGE) \
		$(INSTALLED_BOOTIMAGE_TARGET) \
		$(INSTALLED_RECOVERYIMAGE_TARGET) \
		$(foreach pair,$(BOARD_FLASHFILES),$(call word-colon,1,$(pair))) \
		$(BOARD_FLASHFILES_XML) | $(ACP) \

	$(hide) mkdir -p $(dir $@)
	$(hide) rm -f $@
	$(hide) rm -rf $(ff_intermediates)
	$(hide) mkdir -p $(ff_intermediates)
	$(hide) $(ACP) -f $(BOARD_FLASHFILES_XML) $(INSTALLED_SYSTEMIMAGE) \
		$(INSTALLED_BOOTIMAGE_TARGET) $(INSTALLED_RECOVERYIMAGE_TARGET) \
		$(ff_intermediates)
	$(foreach pair,$(BOARD_FLASHFILES), \
		$(call copy-flashfile,$(call word-colon,1,$(pair)),$(ff_intermediates)/$(call word-colon,2,$(pair))))
	$(hide) zip -qj $@ $(ff_intermediates)/*


$(call dist-for-goals,droidcore,$(flashfiles_zip):$(TARGET_PRODUCT)-flashfiles-$(FILE_NAME_TAG).zip)
.PHONY: flashfiles
flashfiles: $(flashfiles_zip)

endif
