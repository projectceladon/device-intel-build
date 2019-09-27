otp := $(INTEL_PATH_BUILD)/test/ota-test-prepare

.PHONY: publish_resign
publish_resign: dist_files
	export ANDROID_BUILD_TOP=$(PWD); $(otp) -o -s -t $(BUILT_TARGET_FILES_PACKAGE) resigned \
	  && echo "Resign succeed" || { echo "Resign failed"; exit 0; }
	@$(ACP) ota/$(TARGET_PRODUCT)/tfp-resigned.zip $(publish_dest) \
	  && echo "tfp-resigned.zip copy succeed" || echo "tfp-resigned.zip copy failed"
	@$(ACP) ota/$(TARGET_PRODUCT)/flashfiles-resigned.zip $(publish_dest) \
	  && echo "flashfiles-resigned.zip copy succeed" || echo "flashfiles-resigned.zip copy failed"
	@$(ACP) ota/$(TARGET_PRODUCT)/ota-resigned.zip $(publish_dest) \
	  && echo "ota-resigned.zip copy succeed" || echo "ota-resigned.zip copy failed"

publish_ci: publish_resign
