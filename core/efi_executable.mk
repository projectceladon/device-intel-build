ifeq ($(strip $(LOCAL_MODULE_CLASS)),)
LOCAL_MODULE_CLASS := EFI
endif

ifeq ($(strip $(LOCAL_MODULE_SUFFIX)),)
LOCAL_MODULE_SUFFIX := .efi
endif

ifeq ($(strip $(LOCAL_MODULE_PATH)),)
LOCAL_MODULE_PATH := $(PRODUCT_OUT)/efi
endif

ifeq ($(strip $(LOCAL_EFI_KEY_PAIR)),)
LOCAL_EFI_KEY_PAIR := $(INTEL_PATH_BUILD)/testkeys/DB
endif

LOCAL_CC := $(IAFW_CC)
LOCAL_CLANG := true
LOCAL_SANITIZE := never
LOCAL_NO_DEFAULT_COMPILER_FLAGS := true
LOCAL_CFLAGS += $(TARGET_IAFW_GLOBAL_CFLAGS)
LOCAL_ASFLAGS += $(TARGET_IAFW_ASFLAGS)
LOCAL_LDFLAGS := $(TARGET_IAFW_GLOBAL_LDFLAGS) -shared \
	-T $(TARGET_EFI_LDS) $(LOCAL_LDFLAGS)
LOCAL_OBJCOPY_FLAGS := $(TARGET_IAFW_GLOBAL_OBJCOPY_FLAGS) $(LOCAL_OBJCOPY_FLAGS)
LOCAL_EFI_LDFLAGS := $(LOCAL_LDFLAGS)

skip_build_from_source :=
ifdef LOCAL_PREBUILT_MODULE_FILE
ifeq (,$(call if-build-from-source,$(LOCAL_MODULE),$(LOCAL_PATH)))
include $(BUILD_SYSTEM)/prebuilt_internal.mk
skip_build_from_source := true
endif
endif

ifndef skip_build_from_source

ifdef LOCAL_IS_HOST_MODULE
$(error This file should not be used to build host binaries.  Included by (or near) $(lastword $(filter-out config/%,$(MAKEFILE_LIST))))
endif

WITHOUT_LIBCOMPILER_RT := true
include $(BUILD_SYSTEM)/binary.mk
WITHOUT_LIBCOMPILER_RT :=

all_objects += $(intermediates)/db.key $(GNU_EFI_CRT0)

$(intermediates)/db.key: $(LOCAL_EFI_KEY_PAIR).pk8
	$(transform-der-key-to-pem-key)

$(LOCAL_BUILT_MODULE): PRIVATE_OBJCOPY_FLAGS := $(LOCAL_OBJCOPY_FLAGS)
$(LOCAL_BUILT_MODULE): PRIVATE_EFI_KEY_PAIR := $(LOCAL_EFI_KEY_PAIR)
$(LOCAL_BUILT_MODULE): PRIVATE_GENERATED_DB := $(intermediates)/db.key

$(LOCAL_BUILT_MODULE): $(all_objects) $(all_libraries) $(LOCAL_EFI_KEY_PAIR).x509.pem
	$(call transform-o-to-efi-executable,$(PRIVATE_GENERATED_DB),$(PRIVATE_EFI_KEY_PAIR).x509.pem,$(LOCAL_EFI_LDFLAGS))

endif # skip_build_from_source

