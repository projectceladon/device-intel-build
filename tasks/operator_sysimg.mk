echo "start operator system image generation!": $(GEN_OPERATOR_SYSTEM_IMG)
ifeq ($(GEN_OPERATOR_SYSTEM_IMG),true)

ANIMATION_ZIP_PATH := $(dir $(SPLASH_IMG_FILE_PATH))

#SwSc.sh removes the whole operator directory and we need to fix it
$(SYSTEM_FLS): $(BOOTIMG_FLS)

.PHONY: build_operator_system_img

$(SYSTEM_FLS): build_operator_system_img

build_operator_system_img: $(FLSTOOL) $(INTEL_PRG_FILE) systemimage $(INSTALLED_SYSTEMIMAGE) $(FLASHLOADER_FLS)
	@echo "start operator system image generation"
	sh $(CURDIR)/device/intel/build/sofia_lte/generate_operator_system_img.sh  "$(INTEL_PRG_FILE)" "$(INJECT_FLASHLOADER_FLS)" "$(ANIMATION_ZIP_PATH)"

endif

