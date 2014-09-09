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

# Do we have the file we need to add the flash.json to
ifdef INTERNAL_UPDATE_PACKAGE_TARGET
# This makefile process depends on flash.json, which can be located in either:
#    vendor/intel/build/flash.json
#    device/intel/build/flash.json
# Figure out where this makefile (publish.mk) is located and calculate the path
# to flash.json, which is located in the parent directory of our makefile
publish_flash_json := $(abspath $(lastword $(MAKEFILE_LIST)))
publish_flash_json := $(abspath $(dir $(publish_flash_json))/../flash.json)
define publish_zip_flash
zip --junk-paths $(publish_dest)/$(notdir $(INTERNAL_UPDATE_PACKAGE_TARGET)) $(publish_flash_json)
endef

else  # !INTERNAL_UPDATE_PACKAGE_TARGET

# empty definition if we don't have the package file needed to add the
# flash.json to
define publish_zip_flash
endef

endif # !INTERNAL_UPDATE_PACKAGE_TARGET


.PHONY: publish_update_target
# Can we build our publish_update_target file?
ifdef INTERNAL_UPDATE_PACKAGE_TARGET
publish_update_target: publish_mkdir_dest $(INTERNAL_UPDATE_PACKAGE_TARGET)
	@$(ACP) $(INTERNAL_UPDATE_PACKAGE_TARGET) $(publish_dest)
	$(publish_zip_flash)
else  # !INTERNAL_UPDATE_PACKAGE_TARGET
publish_update_target:
	@echo "Warning: Unable to fulfill publish_update_target makefile request"
endif # !INTERNAL_UPDATE_PACKAGE_TARGET


.PHONY: publish_factory_target
# Can we build our publish_factory_target file?
ifdef TARGET_BUILD_INTEL_FACTORY_SCRIPTS
publish_factory_target: publish_mkdir_dest $(FACTORY_SCRIPTS_PACKAGE_TARGET)
	@$(ACP) $(FACTORY_SCRIPTS_PACKAGE_TARGET) $(publish_dest)
else  # !TARGET_BUILD_INTEL_FACTORY_SCRIPTS
publish_factory_target:
	@echo "Warning: Unable to fulfill publish_factory_target makefile request"
endif # !TARGET_BUILD_INTEL_FACTORY_SCRIPTS

.PHONY: publish_flashfiles
ifdef INTEL_FACTORY_FLASHFILES_TARGET
publish_flashfiles: publish_mkdir_dest $(INTEL_FACTORY_FLASHFILES_TARGET)
	@$(ACP) $(INTEL_FACTORY_FLASHFILES_TARGET) $(publish_dest)
else
publish_flashfiles:
	@echo "Warning: Unable to fulfill publish_flashfiles makefile request"
endif


PUBLISH_CI_FILES := $(DIST_DIR)/fastboot $(DIST_DIR)/adb
.PHONY: publish_ci
publish_ci: publish_update_target publish_factory_target publish_flashfiles
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
	$(publish_zip_flash)
