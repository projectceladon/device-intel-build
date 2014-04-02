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

# Error out if we try to use publish/publish_ci but our lunch target does not
# support creating our update package
ifeq (,$(INTERNAL_UPDATE_PACKAGE_TARGET))
    publish_goals := $(strip $(filter publish publish_ci,$(MAKECMDGOALS)))
    ifneq (,$(publish_goals))
	$(error "This lunch target will not support: $(publish_goals)")
    endif
endif

publish_dest := $(TOP)/pub/$(TARGET_PRODUCT)/$(TARGET_BUILD_VARIANT)/

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

publish_make_dir = $(if $(wildcard $1),,mkdir -p $1)

.PHONY: publish_mkdir_dest
publish_mkdir_dest:
	$(call publish_make_dir, $(dir $(publish_dest)))

.PHONY: publish_ci
publish_ci: publish_mkdir_dest $(INTERNAL_UPDATE_PACKAGE_TARGET)
	@$(ACP) $(INTERNAL_UPDATE_PACKAGE_TARGET) $(publish_dest)
	$(publish_zip_flash)

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
