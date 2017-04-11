ifeq ($(TARGET_USE_TESTOS),true)

TARGET_TESTOS_ROOT_OUT := $(PRODUCT_OUT)/testos/root
TESTOS_SELFTEST_PATH := $(TOP)/device/intel/selftest
TESTOS_KERNEL := $(PRODUCT_OUT)/kernel
TESTOSIMAGE_ID_FILE := $(PRODUCT_OUT)/testos.id

# base list for having a bootable image
# list is expanded to include all the shared libraries and required modules
testos_modules := \
        linker \
        mksh \
        systembinsh \
        toolbox \
        gzip \
        adbd \
        watchdogd \
        logcat \
        logd \
        reboot \
        strace \
        toybox \
        sh \
        libstdc++ \
        testos_phony

# files which do not have android modules or files which are "copyfiles"
# and would require one line for each file (e.g. telephony and firmware files)
testos_extra_system_files := \
        $(foreach syspath,$(TARGET_TESTOS_ALL_FROM_SYSTEM_PATHS), \
                $(filter $(TARGET_OUT)/$(syspath)/%, \
                $(ALL_PREBUILT) \
                $(ALL_COPIED_HEADERS) \
                $(ALL_GENERATED_SOURCES) \
                $(ALL_DEFAULT_INSTALLED_MODULES)))

testos_extra_vendor_files := \
        $(foreach vendorpath,$(TARGET_TESTOS_ALL_FROM_VENDOR_PATHS), \
                $(filter $(TARGET_OUT_VENDOR)/$(vendorpath)/%, \
                $(ALL_PREBUILT) \
                $(ALL_COPIED_HEADERS) \
                $(ALL_GENERATED_SOURCES) \
                $(ALL_DEFAULT_INSTALLED_MODULES)))

# Need a special way to get target copyfiles into testos
# filter the needed pairs based on the defined lists
# TARGET_TESTOS_COPY_FILES is a list of file paths in the device
testos_copy_files := \
        $(foreach copyfile, $(TARGET_TESTOS_COPY_FILES), \
                $(filter %:$(copyfile), $(PRODUCT_COPY_FILES)))

# Generates a structure from Android internal dependency list
# Hopefully this is faster than looping through the TARGET_DEPENDENCIES_ON_SHARED_LIBRARIES
# list every time..
define testos-create-dep-structure
$(foreach dep_line, $(TARGET_DEPENDENCIES_ON_SHARED_LIBRARIES),\
        $(eval mod_name := $(firstword $(subst :,$(space),$(dep_line)))) \
        $(eval mod_deps := $(subst $(comma),$(space),$(lastword $(subst :,$(space),$(dep_line))))) \
        $(eval MODULE_DEPS.$(mod_name) := $(mod_deps)) \
)
endef

# Generates a dependency list for the given module list
# $(1): Name of the variable where dependency list is stored
# $(2): List of testos modules
define testos-calc-deps
$(eval _new_dep_modules := $(sort $(filter-out $($(1)),\
        $(foreach m,$(2),$(MODULE_DEPS.$(m))))))\
$(if $(_new_dep_modules),$(eval $(1) += $(_new_dep_modules))\
        $(call testos-calc-deps,$(1),$(_new_dep_modules)))
endef

testos_exp_all := $(testos_modules)
testos_exp_adds := none

# this is a modified copy from the original expand-required-modules
# We would like to use it, but for some reason it doesn't work
# properly from this scope. i.e. we cannot access list by it's name
# this way: $($(listname))
define testos-expand-required-modules
$(eval testos_exp_adds := $(sort $(filter-out $(testos_exp_all),\
        $(foreach m,$(1),$(ALL_MODULES.$(m).REQUIRED)))))\
$(if $(testos_exp_adds),$(eval testos_exp_all += $(testos_exp_adds))\
        $(call testos-expand-required-modules,$(testos_exp_adds)))
endef

define testos-clean-ramdisk
$(foreach file, $(1), \
        rm -rf $(TARGET_TESTOS_ROOT_OUT)/$(file))
endef

NOP := $(call testos-create-dep-structure)

NOP := $(call testos-expand-required-modules, $(testos_modules))

testos_modules = $(testos_exp_all)

NOP := $(call testos-calc-deps, testos_module_deps, $(testos_modules))
testos_modules += $(sort $(testos_module_deps))

# gather a list of files needed to copy into the testos.img
tos_system_files = $(filter $(PRODUCT_OUT)/system%,$(call module-installed-files,$(testos_modules)))

tos_vendor_files = $(filter $(PRODUCT_OUT)/vendor%,$(call module-installed-files,$(testos_modules)))

tos_root_files = $(filter $(PRODUCT_OUT)/root%,$(call module-installed-files,$(testos_modules)))

tos_testos_root_files = $(filter $(PRODUCT_OUT)/testos/root%,$(call module-installed-files,$(testos_modules)))

tos_system_files += $(testos_extra_system_files)
tos_vendor_files += $(testos_extra_vendor_files)

# $(1): source base dir
# $(2): target base dir
# $(3): list name
define testos-copy-files
$(hide) $(foreach srcfile,$(3), \
        destfile=$(patsubst $(1)/%,$(2)/%,$(srcfile)); \
        mkdir -p `dirname $$destfile`; \
        $(ACP) -fdp $(srcfile) $$destfile; \
)
endef

# $(1): out root directory
define testos-copy-copyfiles
$(hide) $(foreach copyfile_str,$(testos_copy_files), \
        src=$(firstword $(subst :, ,$(copyfile_str))); \
        dest=$(word 2, $(subst :, ,$(copyfile_str))); \
        mkdir -p `dirname $(1)/$$dest`; \
        $(ACP) -fdp $$src $(1)/$$dest; \
)
endef

# needed mostly for toybox and toolbox links
define testos-copy-bin-symlinks
        for bin in $(PRODUCT_OUT)/system/bin/*; do [ -h $${bin} ] && cp -P $${bin} $(TARGET_TESTOS_ROOT_OUT)/system/bin/; done
endef

# $(1): target base dir
define testos-copy-kernel-modules
        rm -rf $(1);
        mkdir -p $(1);
        for kernelmodule in $(PRODUCT_OUT)/$(KERNEL_MODULES_ROOT)/*; do cp -P $${kernelmodule} $(1); done
endef

# $(1): list of testos init rc files
define testos-process-init-rcs
        for rcfile in $(1); do echo $${rcfile}; cat $(TESTOS_SELFTEST_PATH)/platform/$${rcfile} >> $(TESTOS_ROOT_OUT)/init.testos.device.rc; done
endef

.PHONY: testos-ramdisk-clean
testos-ramdisk-clean:
	rm -rf $(TESTOS_ROOT_OUT)

$(tos_root_files): testos-ramdisk-clean
$(tos_system_files): testos-ramdisk-clean
$(tos_vendor_files): testos-ramdisk-clean
$(tos_testos_root_files): testos-ramdisk-clean

tos_out := $(PRODUCT_OUT)/testos
TESTOS_ROOT_OUT := $(tos_out)/root
tos_system_out := $(TESTOS_ROOT_OUT)/system
tos_vendor_out := $(TESTOS_ROOT_OUT)/vendor

TESTOS_RAMDISK := $(tos_out)/ramdisk-testos.img.gz
TESTOS_BOOTIMAGE := $(PRODUCT_OUT)/testos.img

$(TESTOS_RAMDISK): \
        kernel \
        device/intel/build/tasks/testos.mk \
        $(BOARD_GPT_BIN) \
        $(BOARD_GPT_MFG_BIN) \
        $(MKBOOTFS) \
        $(INSTALLED_RAMDISK_TARGET) \
        $(MINIGZIP) \
        $(tos_root_files) \
        $(tos_system_files) \
        $(tos_vendor_files) \
        $(tos_testos_root_files)

	$(hide) mkdir -p $(TESTOS_ROOT_OUT)
	$(hide) mkdir -p $(TESTOS_ROOT_OUT)/sbin
	$(hide) mkdir -p $(TESTOS_ROOT_OUT)/tmp
	$(hide) mkdir -p $(TESTOS_ROOT_OUT)/data
	$(hide) mkdir -p $(TESTOS_ROOT_OUT)/mnt
	$(hide) mkdir -p $(TESTOS_ROOT_OUT)/config
	$(hide) mkdir -p $(tos_system_out)
	$(hide) mkdir -p $(tos_system_out)/etc
	$(hide) mkdir -p $(tos_system_out)/bin
	$(hide) mkdir -p $(tos_vendor_out)
	$(hide) $(ACP) -dfr $(TARGET_ROOT_OUT) $(tos_out)
	@echo process testos init rc files
	$(hide) mv $(TARGET_TESTOS_ROOT_OUT)/init.testos.rc $(TARGET_TESTOS_ROOT_OUT)/init.rc
	$(hide) $(call testos-process-init-rcs, $(TARGET_TESTOS_INIT_RC_FILES))
	@echo testos copy system files
	$(hide) $(call testos-copy-files,$(TARGET_OUT),$(tos_system_out),$(tos_system_files))
	@echo testos copy vendor files
	$(hide) $(call testos-copy-files,$(TARGET_OUT_VENDOR),$(tos_vendor_out),$(tos_vendor_files))
	@echo testos copy toybox and toolbox symlinks
	-$(hide) $(call testos-copy-bin-symlinks)
	@echo testos copy kernel modules
	$(hide) $(call testos-copy-kernel-modules,$(TARGET_TESTOS_ROOT_OUT)/lib/modules/)
	$(hide) $(call testos-copy-copyfiles,$(TESTOS_ROOT_OUT))
	$(call testos-clean-ramdisk, $(TESTOS_CLEANUP_LIST))
	$(hide) $(MKBOOTFS) $(TESTOS_ROOT_OUT) | $(MINIGZIP) > $@
	@echo "Created Testos ramdisk: $@"

TESTOS_CMDLINE := g_android.fastboot=0
TESTOS_CMDLINE += $(BOARD_KERNEL_CMDLINE)
TESTOS_CMDLINE += enforcing=0 androidboot.selinux=disabled

INTERNAL_TESTOSIMAGE_ARGS := \
       --kernel $(TESTOS_KERNEL) \
       $(addprefix --second ,$(TESTOS_2NDBOOTLOADER)) \
       --ramdisk $(TESTOS_RAMDISK) \
       --cmdline "$(TESTOS_CMDLINE)"

# Create a standard Android bootimage using the regular kernel and the
# testos ramdisk.
$(TESTOS_BOOTIMAGE): \
        $(TESTOS_KERNEL) \
        $(TESTOS_RAMDISK) \
        $(BOARD_KERNEL_CMDLINE_FILE) \
        $(TESTOS_2NDBOOTLOADER) \
        $(BOOT_SIGNER) \
        $(MKBOOTIMG) \
        $(INSTALLED_BOOTLOADER_MODULE) \
        $(BOARD_FIRST_STAGE_LOADER)

	$(hide) $(MKBOOTIMG)  $(INTERNAL_TESTOSIMAGE_ARGS) \
		     $(BOARD_MKBOOTIMG_ARGS) \
		     --output $@
	@echo "Created Testos bootimage: $@"
##	$(hide) $(ACP) $(BOARD_FIRST_STAGE_LOADER) $(PRODUCT_OUT)/loader.efi
	$(if $(filter true,$(PRODUCTS.$(INTERNAL_PRODUCT).PRODUCT_SUPPORTS_VBOOT)), \
	$(hide) $(MKBOOTIMG) $(INTERNAL_TESTOSIMAGE_ARGS) $(INTERNAL_MKBOOTIMG_VERSION_ARGS) $(BOARD_MKBOOTIMG_ARGS) --output $(TESTOS_BOOTIMAGE).unsigned, \
	$(hide) $(MKBOOTIMG) $(INTERNAL_TESTOSIMAGE_ARGS) $(INTERNAL_MKBOOTIMG_VERSION_ARGS) $(BOARD_MKBOOTIMG_ARGS) --output $(TESTOS_BOOTIMAGE) --id > $(TESTOSIMAGE_ID_FILE))

	$(if $(filter true,$(PRODUCTS.$(INTERNAL_PRODUCT).PRODUCT_SUPPORTS_BOOT_SIGNER)),\
		$(BOOT_SIGNER) /boot $(TESTOS_BOOTIMAGE) $(PRODUCTS.$(INTERNAL_PRODUCT).PRODUCT_VERITY_SIGNING_KEY).pk8 $(PRODUCTS.$(INTERNAL_PRODUCT).PRODUCT_VERITY_SIGNING_KEY).x509.pem $(TESTOS_BOOTIMAGE))
	$(if $(filter true,$(PRODUCTS.$(INTERNAL_PRODUCT).PRODUCT_SUPPORTS_VBOOT)), \
		$(VBOOT_SIGNER) $(FUTILITY) $(TESTOS_BOOTIMAGE).unsigned $(PRODUCTS.$(INTERNAL_PRODUCT).PRODUCT_VBOOT_SIGNING_KEY).vbpubk $(PRODUCTS.$(INTERNAL_PRODUCT).PRODUCT_VBOOT_SIGNING_KEY).vbprivk $(PRODUCTS.$(INTERNAL_PRODUCT).PRODUCT_VBOOT_SIGNING_SUBKEY).vbprivk $(1).keyblock $(TESTOS_BOOTIMAGE))

.PHONY: testos-ramdisk
testos-ramdisk: $(TESTOS_RAMDISK)

.PHONY: testos-bootimage
testos-bootimage: $(TESTOS_BOOTIMAGE)

.PHONY: testosimage
testosimage: $(TESTOS_BOOTIMAGE)
else
testosimage:
endif
