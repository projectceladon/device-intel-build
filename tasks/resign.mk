otp := ./$(INTEL_PATH_BUILD)/test/ota-test-prepare

PUBLISH_RESIGNED_FILES := ota/$(TARGET_PRODUCT)/tfp-resigned.zip \
                          ota/$(TARGET_PRODUCT)/flashfiles-resigned.zip \
                          ota/$(TARGET_PRODUCT)/ota-resigned.zip

COPIED_RESIGNED_FILES := $(publish_dest)/tfp-resigned.zip \
                         $(publish_dest)/flashfiles-resigned.zip \
                         $(publish_dest)/ota-resigned.zip

.PHONY: resign
resign: dist_files
	export ANDROID_BUILD_TOP=$(PWD); $(otp) -l -o -s -t $(BUILT_TARGET_FILES_PACKAGE) resigned && echo "Resign succeed" || { echo "Resign failed"; exit 0; }
# copy in foreach loop fails on server, but succeed locally.
# direct copy with ACP succeed on all systems
#	$(foreach f,$(PUBLISH_RESIGNED_FILES), \
#	  $(if $(wildcard $(f)),echo $(f) " found" && $(ACP) $(f) $(publish_dest);, echo $(f) " not found";))
#	$(foreach f,$(COPIED_RESIGNED_FILES), \
#	  $(if $(wildcard $(f)),echo $(f) " copied"; , echo $(f) " not copied";))
	-$(ACP) ota/$(TARGET_PRODUCT)/tfp-resigned.zip $(publish_dest) && echo "tfp-resigned.zip copy succeed" || echo "tfp-resigned.zip copy failed"
	-$(ACP) ota/$(TARGET_PRODUCT)/flashfiles-resigned.zip $(publish_dest) && echo "flashfiles-resigned.zip copy succeed" || echo "flashfiles-resigned.zip copy failed"
	-$(ACP) ota/$(TARGET_PRODUCT)/ota-resigned.zip $(publish_dest) && echo "ota-resigned.zip copy succeed" || echo "ota-resigned.zip copy failed"

publish_ci: resign
