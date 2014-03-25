# If we're using userfastboot, package up the EFI applications
# so that they can be updated
ifeq ($(TARGET_USE_USERFASTBOOT),true)

UFB_ESP_UPDATE_MK_BLOB := device/intel/build/tasks/mkbblob.py
UFB_ESP_UPDATE_FILES := $(filter %.efi,$(INSTALLED_RADIOIMAGE_TARGET))
UFB_ESP_UPDATE_BLOB := $(OUT)/ufb_esp_update.bin

ifneq ($(UFB_ESP_UPDATE_FILES),)
$(UFB_ESP_UPDATE_BLOB): \
		$(UFB_ESP_UPDATE_FILES) \
		$(UFB_ESP_UPDATE_MK_BLOB)
	$(hide) mkdir -p $(dir $@)
	$(hide) $(UFB_ESP_UPDATE_MK_BLOB) \
			--output $@ \
			$(UFB_ESP_UPDATE_FILES)

.PHONY: ufb_esp
ufb_esp: $(UFB_ESP_UPDATE_BLOB)

droidcore: $(UFB_ESP_UPDATE_BLOB)
$(call dist-for-goals,droidcore,$(UFB_ESP_UPDATE_BLOB):$(TARGET_PRODUCT)-ufb_esp_update-$(FILE_NAME_TAG).bin)

endif # efi binaries present
endif # TARGET_USE_USERFASTBOOT=true

