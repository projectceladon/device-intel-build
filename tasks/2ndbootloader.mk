ifndef BOARD_BLOBSTORE_CONFIG
LOCAL_DTB_PATH := $(LOCAL_KERNEL_PATH)/$(BOARD_DTB_FILE)
else
LOCAL_DTB_PATH := $(PRODUCT_OUT)/blobstore.bin
$(LOCAL_DTB_PATH):
	device/intel/build/build_blobstore.py \
			--config $(BOARD_BLOBSTORE_CONFIG) \
			--output $(LOCAL_DTB_PATH)
endif

$(INSTALLED_2NDBOOTLOADER_TARGET): $(LOCAL_DTB_PATH) | $(ACP)
	$(hide) $(ACP) -fp $(LOCAL_DTB_PATH) $@
