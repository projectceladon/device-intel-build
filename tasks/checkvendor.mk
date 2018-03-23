# Target checkvendor will be built in latest builds (when target publish is built)
.PHONY: checkvendor
checkvendor:
	@$(INTEL_PATH_BUILD)/tasks/checkvendor.py -l -p vendor/intel

publish_ci: checkvendor

