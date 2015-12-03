ifdef BOARD_BLOBSTORE_CONFIG

build_blobstore := device/intel/build/build_blobstore.py
blobstore_deps := $(build_blobstore) device/intel/build/blobstore.py $(BOARD_BLOBSTORE_CONFIG)
ifdef BOARD_DEVICE_MAPPING
blobstore_deps += $(BOARD_DEVICE_MAPPING)
blobstore_extra_args := --device-map $(BOARD_DEVICE_MAPPING)
endif
ifdef TARGET_PRODUCT_FISHNAME
blobstore_extra_args += --fishname $(TARGET_PRODUCT_FISHNAME)
endif

# use the dtb file(s) under LOCAL_KERNEL_PATH
# if dtb file is built from kernel source
ifeq ($(BUILD_DTBS), true)
blobstore_extra_args += --dtb-path $(LOCAL_KERNEL_PATH)
$(foreach v,$(BOARD_DTB_VARIANTS), \
    $(eval $(if $$(BOARD_DTB.$(v)), blobstore_deps += $$(BOARD_DTB.$(v)))))
else
# build_blobstore without an output parameter lists all the necessary
# source blob files we need
blobstore_deps += $(shell $(build_blobstore) \
			--config $(BOARD_BLOBSTORE_CONFIG) \
			$(blobstore_extra_args))
endif

$(INSTALLED_2NDBOOTLOADER_TARGET): $(blobstore_deps)
	$(build_blobstore) --config $(BOARD_BLOBSTORE_CONFIG) \
			$(blobstore_extra_args) --output $@
else ifdef BOARD_DTB_FILE
# Non-scalable SoFIA targets

ifneq ($(TARGET_DEVICE),Sf3gr_sr_garnet)
LOCAL_DTB_PATH := $(LOCAL_KERNEL_PATH)/$(BOARD_DTB_FILE)
else
LOCAL_DTB_PATH := $(BOARD_DTB)
$(INSTALLED_2NDBOOTLOADER_TARGET): $(INSTALLED_KERNEL_TARGET)
endif

ifeq ($(USE_IMC_BUILD_RULES),true)
.PHONY: kernel_dtb
kernel_dtb: $(INSTALLED_2NDBOOTLOADER_TARGET)
endif

$(INSTALLED_2NDBOOTLOADER_TARGET): $(LOCAL_DTB_PATH) | $(ACP)
	$(hide) $(ACP) -fp $(LOCAL_DTB_PATH) $@

else ifdef BOARD_OEM_VARS
# Non-scalable EFI targets that use oemvars

$(INSTALLED_2NDBOOTLOADER_TARGET): $(BOARD_OEM_VARS)
	$(hide) echo "#OEMVARS" > $@
	$(hide) cat $(BOARD_OEM_VARS) >> $@

endif
