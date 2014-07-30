PUBLISH_SCRIPTS := device/intel/build

FLASHFILES_CONFIG ?= $(TARGET_DEVICE_DIR)/flashfiles.json

ifneq ($(wildcard $(FLASHFILES_CONFIG)),)

$(eval FLASHFILES_T2F := $(shell $(PUBLISH_SCRIPTS)/flashdep.py $(FLASHFILES_CONFIG)))

FLASHFILES_IMAGES := $(foreach dep,$(FLASHFILES_T2F),$(word 2,$(subst :, ,$(dep))))

FLASHFILES_XML := $(shell $(PUBLISH_SCRIPTS)/flashtarget.py $(FLASHFILES_CONFIG))
FLASHFILES_XML := $(addprefix $(PRODUCT_OUT)/,$(FLASHFILES_XML))
FIRST_FLASHFILES_XML := $(firstword $(FLASHFILES_XML))
OTHER_FLASHFILES_XML := $(wordlist 2,99,$(FLASHFILES_XML))

# Makefile cannot handle 1 command with multiple output, so use the first one
$(FIRST_FLASHFILES_XML): $(FLASHFILES_CONFIG) $(FLASHFILES_IMAGES)
	$(hide) ./$(PUBLISH_SCRIPTS)/flashxml.py $< -p $(TARGET_PRODUCT) -d $(@D) -t "$(FLASHFILES_T2F)"

# Add dependency for other xmls
$(OTHER_FLASHFILES_XML): $(FIRST_FLASHFILES_XML)

.PHONY: flashfiles_nozip
flashfiles_nozip: $(FLASHFILES_XML) $(FLASHFILES_IMAGES)

FLASHFILES_ZIP := $(PRODUCT_OUT)/flashfiles.zip

$(FLASHFILES_ZIP): $(FLASHFILES_IMAGES) $(FLASHFILES_XML)
	$(hide) mkdir -p $(@D)
	$(hide) rm -f $@
	@echo generating $@
	$(hide) zip -1 -j $@ $^

$(call dist-for-goals,droidcore,$(FLASHFILES_ZIP):$(TARGET_PRODUCT)-flashfiles-$(FILE_NAME_TAG).zip)

.PHONY: flashfiles
flashfiles: $(FLASHFILES_ZIP)

endif
