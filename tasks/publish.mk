# This provides the 'publish' and 'publish_ci' makefile targets.
#
# PUBLISH target:
# 	NOTE: When using the 'publish' target you MUST also use the 'dist'
# 	target.  The 'dist' target is a special target and unfortunately we
# 	can't just depend on the 'dist' target :(
# 	   e.g. 'make dist publish'
# 	   e.g. 'make droid dist publish'
#
# 	DO NOT DO: 'make publish' as it will not work
#
# PUBLISH_CI target:
# 	The 'publish_ci' target may be called by itself as it has a dependency
# 	on the one file we need.
# 	   e.g. 'make publish_ci'

publish_dest := $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/
publish_make_dir = $(if $(wildcard $1),,mkdir -p $1)

.PHONY: publish_mkdir_dest
publish_mkdir_dest:
	$(call publish_make_dir, $(dir $(publish_dest)))

# Publish System symbols
PUB_SYSTEM_SYMBOLS := $(publish_dest)/symbols.tar.gz

$(PUB_SYSTEM_SYMBOLS): systemtarball
	@echo "Publish system symbols"
	$(hide) mkdir -p $(@D)
	tar --checkpoint=1000 --checkpoint-action=dot -czf $@ $(PRODUCT_OUT)/symbols

.PHONY: publish_system_symbols
publish_system_symbols: $(PUB_SYSTEM_SYMBOLS)

.PHONY: publish_kernel_debug
ifeq ($(TARGET_PREBUILT_KERNEL),)
# Publish Kernel debug
PUB_KERNEL_DBG := vmlinux.bz2 System.map.bz2
PUB_KERNEL_DBG_PATH := $(publish_dest)/kernel
PUB_KERNEL_DBG := $(addprefix $(PUB_KERNEL_DBG_PATH)/,$(PUB_KERNEL_DBG))

$(PUB_KERNEL_DBG_PATH)/%: $(LOCAL_KERNEL)| $(ACP)
	@echo "Publish $(basename $(@F))"
	$(hide) mkdir -p $(@D)
	$(hide) bzip2 -c $(LOCAL_KERNEL_PATH)/$(basename $(@F)) > $@

PUB_KERNEL_MODULES = $(PUB_KERNEL_DBG_PATH)/kernel_modules-$(TARGET_BUILD_VARIANT).tar.bz2

$(PUB_KERNEL_MODULES): copy_modules
	@echo "Publish Kernel Modules"
	$(hide) mkdir -p $(@D)
	-tar --checkpoint=1000 --checkpoint-action=dot -cjf $@ -C $(LOCAL_KERNEL_PATH)/lib/modules .

publish_kernel_debug: $(PUB_KERNEL_DBG) $(PUB_KERNEL_MODULES)
	@echo "Publish kernel debug: $(notdir $^)"
else
publish_kernel_debug:
	@echo "Publish kernel debug: skipped"
endif

# Publish OS agnostic tag
ifneq ($(OS_AGNOSTIC_INFO),)
PUB_OSAGNOSTIC_TAG := $(publish_dest)/$(notdir $(OS_AGNOSTIC_INFO))
$(PUB_OSAGNOSTIC_TAG): publish_mkdir_dest $(OS_AGNOSTIC_INFO)
	$(hide)($(ACP) $(OS_AGNOSTIC_INFO) $@)
endif

# Publish Firmware symbols
.PHONY: publish_firmware_symbols
ifneq ($(FIRMWARE_SYMBOLS_PATH),)
publish_firmware_symbols: publish_mkdir_dest
	@echo "Publish firmware symbols"
	$(hide)(zip -qry $(publish_dest)/$(FIRMWARE_SYMBOLS_FILE) $(FIRMWARE_SYMBOLS_PATH))
endif

# Are we doing an 'sdk' type lunch target
PUBLISH_SDK := $(strip $(filter sdk sdk_x86,$(TARGET_PRODUCT)))

ifndef PUBLISH_SDK

.PHONY: publish_flashfiles
ifdef INTEL_FACTORY_FLASHFILES_TARGET
publish_flashfiles: publish_mkdir_dest $(INTEL_FACTORY_FLASHFILES_TARGET)
	@$(ACP) $(INTEL_FACTORY_FLASHFILES_TARGET) $(publish_dest)
else
publish_flashfiles:
	@echo "Warning: Unable to fulfill publish_flashfiles makefile request"
endif

.PHONY:publish_ifwi
ifeq ($(USE_INTEL_FLASHFILES),false)
publish_ifwi:
	@echo "Warning: Unable to fulfill publish_ifwi makefile request"
endif

.PHONY: publish_liveimage
ifdef INTEL_LIVEIMAGE_TARGET
publish_liveimage: publish_mkdir_dest $(INTEL_LIVEIMAGE_TARGET)
	@$(ACP) $(INTEL_LIVEIMAGE_TARGET) $(publish_dest)
else
publish_liveimage:
	@echo "Warning: Unable to fulfill publish_liveimage makefile request"
endif

.PHONY: publish_gptimage
ifdef GPTIMAGE_BIN
publish_gptimage: publish_mkdir_dest $(GPTIMAGE_BIN)
	@$(ACP) $(GPTIMAGE_BIN) $(publish_dest)
else
publish_gptimage:
	@echo "Warning: Unable to fulfill publish_gptimage makefile request"
endif

.PHONY: publish_otapackage
publish_otapackage: publish_mkdir_dest $(INTERNAL_OTA_PACKAGE_TARGET)
	@$(ACP) $(INTERNAL_OTA_PACKAGE_TARGET) $(publish_dest)

.PHONY: publish_ota_targetfiles
publish_ota_targetfiles: publish_mkdir_dest $(BUILT_TARGET_FILES_PACKAGE)
	@$(ACP) $(BUILT_TARGET_FILES_PACKAGE) $(publish_dest)

.PHONY: publish_ota_flashfile
ifneq ($(PUBLISH_CONF),)
BUILDBOT_PUBLISH_DEPS := $(shell python -c 'import json,os ; print " ".join(json.loads(os.environ["PUBLISH_CONF"]).get("$(TARGET_BUILD_VARIANT)",[]))')

# Translate buildbot target to makefile target
publish_ota_flashfile: $(BUILDBOT_PUBLISH_DEPS)

full_ota: publish_otapackage
full_ota_flashfile:
ota_target_files: publish_ota_targetfiles
system_img:
else
publish_ota_flashfile:
	@echo "Do not publish ota_flashfile"
endif # PUBLISH_CONF

PUBLISH_CI_FILES := $(DIST_DIR)/fastboot $(DIST_DIR)/adb
.PHONY: publish_ci
publish_ci: publish_flashfiles publish_liveimage publish_ota_flashfile publish_gptimage publish_ifwi publish_firmware_symbols $(PUB_OSAGNOSTIC_TAG)
	$(if $(wildcard $(publish_dest)), \
	  $(foreach f,$(PUBLISH_CI_FILES), \
	    $(if $(wildcard $(f)),$(ACP) $(f) $(publish_dest);,)),)


else # !PUBLISH_SDK
# Unfortunately INTERNAL_SDK_TARGET is always defined, so its existence does
# not indicate that we are building the SDK

.PHONY: publish_ci
publish_ci: publish_sdk_target


.PHONY: publish_sdk_target
publish_sdk_target: publish_mkdir_dest $(INTERNAL_SDK_TARGET)
	@$(ACP) $(INTERNAL_SDK_TARGET) $(publish_dest)


endif # !PUBLISH_SDK


# We need to make sure our 'publish' target depends on the other targets so
# that it will get done at the end.  Logic copied from build/core/distdir.mk
PUBLISH_GOALS := $(strip $(filter-out publish publish_ci,$(MAKECMDGOALS)))
PUBLISH_GOALS := $(strip $(filter-out $(INTERNAL_MODIFIER_TARGETS),$(PUBLISH_GOALS)))
ifeq (,$(PUBLISH_GOALS))
# The commandline was something like "make publish" or "make publish showcommands".
# Add a dependency on a real target.
PUBLISH_GOALS := $(DEFAULT_GOAL)
endif

.PHONY: publish
publish: publish_mkdir_dest $(PUBLISH_GOALS) publish_ifwi publish_firmware_symbols $(PUB_OSAGNOSTIC_TAG)
	@$(ACP) $(DIST_DIR)/* $(publish_dest)
