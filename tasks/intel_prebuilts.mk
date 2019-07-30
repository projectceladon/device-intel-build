ifneq ($(TARGET_OUT_prebuilts),)
intel_prebuilts_top_makefile := $(TARGET_OUT_prebuilts)/Android.mk
$(intel_prebuilts_top_makefile):
	@mkdir -p $(dir $@)
	@echo 'LOCAL_PATH := $$(call my-dir)' > $@
	@echo 'ifeq ($$(TARGET_ARCH),x86)' >> $@
	@echo 'include $$(shell find $$(LOCAL_PATH) -mindepth 2 -name "Android.mk")' >> $@
	@echo 'endif' >> $@
endif

.PHONY: intel_prebuilts publish_intel_prebuilts generate_intel_prebuilts
intel_prebuilts: $(filter-out intel_prebuilts, $(MAKECMDGOALS))
	@$(MAKE) publish_intel_prebuilts

publish_intel_prebuilts: generate_intel_prebuilts

generate_intel_prebuilts: $(intel_prebuilts_top_makefile)
	@$(if $(TARGET_OUT_prebuilts), \
		echo did make following prebuilts Android.mk: \
		$(foreach m, $?,\
			echo "    " $(m);) \
		find $(TARGET_OUT_prebuilts) -name Android.mk -print -exec cat {} \;)


PUB_INTEL_PREBUILTS := prebuilts.zip

EXTERNAL_CUSTOMER ?= "g"

INTEL_PREBUILTS_LIST := $(shell repo forall -g bsp-priv -a $(EXTERNAL_CUSTOMER)_external=bin -p -c echo 2> /dev/null)
INTEL_PREBUILTS_LIST := $(filter-out project,$(INTEL_PREBUILTS_LIST))
INTEL_PREBUILTS_LIST := $(addprefix prebuilts/intel/, $(subst /PRIVATE/,/prebuilts/$(REF_PRODUCT_NAME)/,$(INTEL_PREBUILTS_LIST)))
INTEL_PREBUILTS_LIST += prebuilts/intel/Android.mk

.PHONY: $(PUB_INTEL_PREBUILTS)
$(PUB_INTEL_PREBUILTS): generate_intel_prebuilts
	@echo "Publish prebuilts for external release"
	$(hide) rm -f $(abspath pub/$(TARGET_PRODUCT)/$@)
	$(hide) mkdir -p $(abspath pub/$(TARGET_PRODUCT))
	$(hide) cd $(PRODUCT_OUT) && zip -r $(abspath pub/$(TARGET_PRODUCT)/$@) $(INTEL_PREBUILTS_LIST)

# publish external if buildbot set EXTERNAL_BINARIES env variable
# and only for userdebug
ifeq (userdebug,$(TARGET_BUILD_VARIANT))
ifeq ($(EXTERNAL_BINARIES),true)
publish_intel_prebuilts: $(PUB_INTEL_PREBUILTS)
endif
endif
