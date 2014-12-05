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

.PHONY: publish_liveimage
ifdef INTEL_LIVEIMAGE_TARGET
publish_liveimage: publish_mkdir_dest $(INTEL_LIVEIMAGE_TARGET)
	@$(ACP) $(INTEL_LIVEIMAGE_TARGET) $(publish_dest)
else
publish_liveimage:
	@echo "Warning: Unable to fulfill publish_liveimage makefile request"
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
publish_ci: publish_flashfiles publish_liveimage publish_ota_flashfile
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
publish: publish_mkdir_dest $(PUBLISH_GOALS)
	@$(ACP) $(DIST_DIR)/* $(publish_dest)
