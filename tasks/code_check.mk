


flashfiles: warn_vendor_modules warn_local_module_tags
publish_ci: warn_vendor_modules warn_local_module_tags

.PHONY: warn_vendor_modules warn_local_module_tags
# for each module in $(DELINQUANT_VENDOR_MODULES) if LOCAL_MODULE_INSTALLED exists, warn
warn_vendor_modules:
	@for i in $(DELINQUANT_VENDOR_MODULES); \
	do echo [NOT IN VENDOR][$$TARGET_PRODUCT]\
	module:`echo $$i | cut -d: -f1` installed in:`echo $$i | cut -d: -f2` \
	by:`echo $$i | cut -d: -f3` should be installed either in /system/vendor \
	or /vendor; done

warn_local_module_tags:
	@for i in $(DELINQUANT_TAGS_MODULES); \
	do echo [LOCAL_MODULE_TAGS][$$TARGET_PRODUCT]\
	`echo $$i | cut -d: -f1` have LOCAL_MODULE_TAGS := `echo $$i | cut -d: -f2` \
	defined in `echo $$i | cut -d: -f3`; done
