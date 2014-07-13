LOCAL_PATH := $(call my-dir)

# the signapk tool (a .jar application used to sign packages)
# ============================================================
include $(CLEAR_VARS)
LOCAL_MODULE := signapk_intel
LOCAL_MODULE_STEM := signapk
LOCAL_MODULE_PATH := out/host/intel/framework
LOCAL_SRC_FILES := SignApk.java
LOCAL_JAR_MANIFEST := SignApk.mf
include $(BUILD_HOST_JAVA_LIBRARY)

$(call dist-for-goals,dist_files,$(LOCAL_INSTALLED_MODULE))
