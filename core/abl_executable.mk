ifeq ($(strip $(LOCAL_MODULE_CLASS)),)
LOCAL_MODULE_CLASS := ABL
endif

ifeq ($(strip $(LOCAL_MODULE_SUFFIX)),)
LOCAL_MODULE_SUFFIX := .abl
endif

ifeq ($(strip $(LOCAL_MODULE_PATH)),)
LOCAL_MODULE_PATH := $(PRODUCT_OUT)/abl
endif

LOCAL_CC := $(IAFW_CC)
LOCAL_CLANG := true
LOCAL_SANITIZE := never
LOCAL_NO_DEFAULT_COMPILER_FLAGS := true
LOCAL_CFLAGS += $(TARGET_IAFW_GLOBAL_CFLAGS)
LOCAL_ASFLAGS += $(TARGET_IAFW_ASFLAGS)
LOCAL_LDFLAGS := $(TARGET_IAFW_GLOBAL_LDFLAGS) -static \
	-T $(TARGET_ABL_LDS) $(LOCAL_LDFLAGS)
# If kernel enforce superpages the .text section gets aligned at
# offset 0x200000 which break multiboot compliance.
LOCAL_LDFLAGS += -z max-page-size=0x1000
LOCAL_ABL_LDFALGS := $(LOCAL_LDFLAGS)
LOCAL_OBJCOPY_FLAGS := $(TARGET_IAFW_GLOBAL_OBJCOPY_FLAGS) $(LOCAL_OBJCOPY_FLAGS)

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

LIBPAYLOAD_CRT0_LIB := $(call intermediates-dir-for,STATIC_LIBRARIES,$(LIBPAYLOAD_CRT0))/$(LIBPAYLOAD_CRT0).a
all_objects += $(LIBPAYLOAD_CRT0_LIB)

$(LOCAL_BUILT_MODULE): PRIVATE_OBJCOPY_FLAGS := $(LOCAL_OBJCOPY_FLAGS)

#$(LOCAL_BUILT_MODULE): $(all_objects) $(all_libraries) $(ABLIMAGE) $(ABLSIGN)
$(LOCAL_BUILT_MODULE): $(all_objects) $(all_libraries)
	$(call transform-o-to-sbl-executable,$(LOCAL_ABL_LDFALGS))

endif # skip_build_from_source

