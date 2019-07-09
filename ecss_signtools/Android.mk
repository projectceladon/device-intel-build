LOCAL_PATH := $(call my-dir)

HOST_ECSS_OUT := $(HOST_OUT)/ecss
HOST_ECSS_OUT_EXECUTABLES := $(HOST_ECSS_OUT)/bin
HOST_ECSS_OUT_JAVA_LIBRARIES := $(HOST_ECSS_OUT)/framework

.PHONY: host-ecss-tools
host-ecss-tools: \
		$(HOST_ECSS_OUT_EXECUTABLES)/verity_signer \
		$(HOST_ECSS_OUT_EXECUTABLES)/boot_signer \
		$(HOST_ECSS_OUT_EXECUTABLES)/keystore_signer \
		$(HOST_ECSS_OUT_JAVA_LIBRARIES)/makepk8_ecss.jar \
		$(HOST_ECSS_OUT_JAVA_LIBRARIES)/dumpkey.jar

# JCE provider that redirects to the Intel Enterprise Code Signing System
# (ECSS) instead of local software crypto.
include $(CLEAR_VARS)
LOCAL_MODULE := intel-ecss-jce-provider
LOCAL_MODULE_TAGS := optional
LOCAL_SRC_FILES := $(call all-java-files-under,provider/src)
LOCAL_JAVACFLAGS := -encoding UTF-8 -Xlint:deprecation
LOCAL_JAVA_LIBRARIES := bouncycastle-host bouncycastle-bcpkix-host bouncycastle-host
LOCAL_ADDITIONAL_DEPENDENCIES := $(LOCAL_PATH)/Android.mk
include $(BUILD_HOST_JAVA_LIBRARY)

# Utility to create a PKCS #8 blob that contains references to the Intel
# Enterprise Code Signing System (ECSS) instead of the actual key material
# itself.
include $(CLEAR_VARS)
LOCAL_MODULE := makepk8_ecss
LOCAL_SRC_FILES := makepk8/MakePk8.java
LOCAL_JAR_MANIFEST := makepk8/MakePk8.mf
LOCAL_MODULE_PATH := $(HOST_ECSS_OUT_JAVA_LIBRARIES)
LOCAL_STATIC_JAVA_LIBRARIES := bouncycastle-host bouncycastle-bcpkix-host
include $(BUILD_HOST_JAVA_LIBRARY)

# Special build of the standard signapk tool that includes the
# intel-ecss-jce-provider libraries so we can redirect it to Intel production
# signing servers by passing
#   -providerClass com.intel.ecss.provider.IntelECSSProvider
# to signapk. This is necessary because the JVM ignores $CLASSPATH, -cp, and
# -classpath inputs if the -jar option is used to run a Java app.
#
# Minor change to signapk to remove code to force use of the BouncyCastle
# crypto provider regardless of the key type.
include $(CLEAR_VARS)
LOCAL_MODULE := signapk_ecss
LOCAL_SRC_FILES := $(call all-java-files-under, signapk)
LOCAL_JAR_MANIFEST := signapk/SignApk.mf
LOCAL_MODULE_PATH := $(HOST_ECSS_OUT_JAVA_LIBRARIES)
LOCAL_STATIC_JAVA_LIBRARIES := bouncycastle-host bouncycastle-bcpkix-host intel-ecss-jce-provider
include $(BUILD_HOST_JAVA_LIBRARY)

ifeq ($(TARGET_BUILD_APPS),)
# The post-build signing tools need signapk.jar, but we don't
# need this if we're just doing unbundled apps.
$(call dist-for-goals,droidcore,$(LOCAL_INSTALLED_MODULE))
endif
#$(call dist-for-goals,dist_files,$(LOCAL_INSTALLED_MODULE))

# Special build of signing tools from system/extras/verity that:
# - Include intel-ecss-jce-provider libraries to enable redirecting signatures
#   to Intel production signing servers
# - Add support for -providerClass parameters (signapk equivalent) to add
#   out custom crypto provider at runtime.

include $(CLEAR_VARS)
LOCAL_SRC_FILES := verity/VeritySigner.java verity/Utils.java
LOCAL_MODULE := VeritySigner_ecss
LOCAL_JAR_MANIFEST := verity/VeritySigner.mf
LOCAL_MODULE_TAGS := optional
LOCAL_MODULE_PATH := $(HOST_ECSS_OUT_JAVA_LIBRARIES)
LOCAL_STATIC_JAVA_LIBRARIES := bouncycastle-host bouncycastle-bcpkix-host intel-ecss-jce-provider
include $(BUILD_HOST_JAVA_LIBRARY)

include $(CLEAR_VARS)
LOCAL_SRC_FILES := verity/BootSignature.java verity/VeritySigner.java verity/Utils.java
LOCAL_MODULE := BootSignature_ecss
LOCAL_JAR_MANIFEST := verity/BootSignature.mf
LOCAL_MODULE_TAGS := optional
LOCAL_MODULE_PATH := $(HOST_ECSS_OUT_JAVA_LIBRARIES)
LOCAL_STATIC_JAVA_LIBRARIES := bouncycastle-host bouncycastle-bcpkix-host intel-ecss-jce-provider
include $(BUILD_HOST_JAVA_LIBRARY)

include $(CLEAR_VARS)
LOCAL_SRC_FILES := verity/BootSignature.java verity/KeystoreSigner.java verity/Utils.java
LOCAL_MODULE := BootKeystoreSigner_ecss
LOCAL_JAR_MANIFEST := verity/KeystoreSigner.mf
LOCAL_MODULE_TAGS := optional
LOCAL_MODULE_PATH := $(HOST_ECSS_OUT_JAVA_LIBRARIES)
LOCAL_STATIC_JAVA_LIBRARIES := bouncycastle-host bouncycastle-bcpkix-host intel-ecss-jce-provider
include $(BUILD_HOST_JAVA_LIBRARY)

include $(CLEAR_VARS)
LOCAL_SRC_FILES := verity/verity_signer
LOCAL_MODULE := verity_signer
LOCAL_MODULE_CLASS := ECSS_EXECUTABLES
LOCAL_IS_HOST_MODULE := true
LOCAL_MODULE_TAGS := optional
LOCAL_MODULE_PATH := $(HOST_ECSS_OUT_EXECUTABLES)
LOCAL_REQUIRED_MODULES := VeritySigner_ecss
include $(BUILD_PREBUILT)

include $(CLEAR_VARS)
LOCAL_SRC_FILES := verity/boot_signer
LOCAL_MODULE := boot_signer
LOCAL_MODULE_CLASS := ECSS_EXECUTABLES
LOCAL_IS_HOST_MODULE := true
LOCAL_MODULE_TAGS := optional
LOCAL_MODULE_PATH := $(HOST_ECSS_OUT_EXECUTABLES)
LOCAL_REQUIRED_MODULES := BootSignature_ecss
include $(BUILD_PREBUILT)

include $(CLEAR_VARS)
LOCAL_SRC_FILES := verity/keystore_signer
LOCAL_MODULE := keystore_signer
LOCAL_MODULE_CLASS := ECSS_EXECUTABLES
LOCAL_IS_HOST_MODULE := true
LOCAL_MODULE_TAGS := optional
LOCAL_MODULE_PATH := $(HOST_ECSS_OUT_EXECUTABLES)
LOCAL_REQUIRED_MODULES := BootKeystoreSigner_ecss
include $(BUILD_PREBUILT)

# copy dumpkey from the standard framework to the ecss/framework because
# sign_target_files_apks will prepend a search path including the bin
# directory, but not the framework directory containing jars.
#
$(HOST_ECSS_OUT_JAVA_LIBRARIES)/dumpkey.jar: $(HOST_OUT_JAVA_LIBRARIES)/dumpkey.jar
	mkdir -p $(HOST_ECSS_OUT_JAVA_LIBRARIES)
	cp $< $@
