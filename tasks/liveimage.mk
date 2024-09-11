# Determine if we are doing a 'make liveimage'
LIVEIMAGE_GOAL := $(strip $(filter liveimage,$(MAKECMDGOALS)))

ifeq (liveimage,$(LIVEIMAGE_GOAL))
name := $(TARGET_PRODUCT)
ifeq ($(TARGET_BUILD_TYPE),debug)
  name := $(name)_debug
endif
name := $(name)-liveimage-$(FILE_NAME_TAG)
INTEL_LIVEIMAGE_TARGET := $(PRODUCT_OUT)/$(name).img
$(call dist-for-goals,liveimage,$(INTEL_LIVEIMAGE_TARGET))

ifeq ($(TARGET_UEFI_ARCH),i386)
efi_default_name := bootia32.efi
else
efi_default_name := bootx64.efi
endif

ramdisk_dir := $(call intermediates-dir-for,PACKAGING,live-ramdisk)
live_artifact_dir := $(call intermediates-dir-for,PACKAGING,live-image-items)
sfs_dir := $(call intermediates-dir-for,PACKAGING,live-sfs)
disk_dir := $(live_artifact_dir)/root

live_ramdisk := $(live_artifact_dir)/ramdisk-live.img
live_bootimage := $(live_artifact_dir)/boot-live.img
live_sfs := $(live_artifact_dir)/images.sfs
liveimage_zip := $(live_artifact_dir)/live.zip

$(live_sfs): \
		$(INTEL_PATH_BUILD)/tasks/liveimage.mk \
		$(INSTALLED_SYSTEMIMAGE) \
		$(HOST_OUT_EXECUTABLES)/simg2img \
		| $(ACP) \

	$(hide) mkdir -p $(dir $@)
	$(hide) rm -rf $(sfs_dir)
	$(hide) mkdir -p $(sfs_dir)
ifeq ($(TARGET_USERIMAGES_SPARSE_EXT_DIABLED),true)
	$(hide) $(ACP) $(INSTALLED_SYSTEMIMAGE) $(sfs_dir)/system.img
else
	$(hide) $(HOST_OUT_EXECUTABLES)/simg2img $(INSTALLED_SYSTEMIMAGE) $(sfs_dir)/system.img
endif
	$(hide) PATH=/sbin:/usr/sbin:$(PATH) mksquashfs $(sfs_dir) $@ -no-recovery -noappend

live_initrc := $(INTEL_PATH_COMMON)/boot/init.live.rc

$(live_ramdisk): \
		$(INTEL_PATH_BUILD)/tasks/liveimage.mk \
		$(PRODUCT_OUT)/preinit/preinit \
		$(INSTALLED_RAMDISK_TARGET) \
		$(MKBOOTFS) \
		$(live_initrc) \
		| $(GZIP) $(ACP) \

	$(hide) mkdir -p $(dir $@)
	$(hide) rm -rf $(ramdisk_dir)
	$(hide) mkdir -p $(ramdisk_dir)
	$(hide) $(ACP) -rfd $(TARGET_ROOT_OUT)/* $(ramdisk_dir)
	$(hide) mv $(ramdisk_dir)/init $(ramdisk_dir)/init2
	$(hide) $(ACP) -p $(PRODUCT_OUT)/preinit/preinit $(ramdisk_dir)/init
	$(hide) mkdir -p $(ramdisk_dir)/installmedia
	$(hide) mkdir -p $(ramdisk_dir)/tmp
	$(hide) echo "import init.live.rc" >> $(ramdisk_dir)/init.rc
	$(hide) sed -i -r 's/^[\t ]*(mount_all|mount yaffs|mount ext).*//g' $(ramdisk_dir)/init*.rc
	$(hide) $(ACP) $(live_initrc) $(ramdisk_dir)
	$(hide) $(MKBOOTFS) $(ramdisk_dir) | $(GZIP) > $@

$(live_bootimage): \
		$(INTEL_PATH_BUILD)/tasks/liveimage.mk \
		$(INSTALLED_KERNEL_TARGET) \
		$(live_ramdisk) \
		$(MKBOOTIMG) $(BOOT_SIGNER) \

	$(hide) mkdir -p $(dir $@)
	$(hide) $(MKBOOTIMG) --kernel $(INSTALLED_KERNEL_TARGET) \
			--ramdisk $(live_ramdisk) \
			--cmdline "$(BOARD_KERNEL_CMDLINE)" \
			$(BOARD_MKBOOTIMG_ARGS) \
			--output $@
	$(hide) $(BOOT_SIGNER) /fastboot $@ $(PRODUCTS.$(INTERNAL_PRODUCT).PRODUCT_VERITY_SIGNING_KEY).pk8 $(PRODUCTS.$(INTERNAL_PRODUCT).PRODUCT_VERITY_SIGNING_KEY).x509.pem $@

$(liveimage_zip): \
		$(INTEL_PATH_BUILD)/tasks/liveimage.mk \
		$(live_sfs) \
		$(BOARD_FIRST_STAGE_LOADER) \
		$(BOARD_EFI_MODULES) \

	$(hide) mkdir -p $(dir $@)
	$(hide) rm -rf $(disk_dir)
	$(hide) mkdir -p $(disk_dir)
	$(hide) $(ACP) -f $(live_sfs) $(disk_dir)/images.sfs
	$(hide) mkdir -p $(disk_dir)/images
	$(hide) mkdir -p $(disk_dir)/EFI/BOOT
	$(hide) touch $(disk_dir)/iago-cookie
ifneq ($(BOARD_EXTRA_EFI_MODULES),)
	$(hide) $(ACP) $(BOARD_EXTRA_EFI_MODULES) $(disk_dir)/
endif
	$(hide) $(ACP) $(BOARD_FIRST_STAGE_LOADER) $(disk_dir)/EFI/BOOT/$(efi_default_name)
	$(hide) (cd $(disk_dir) && zip -qry ../$(notdir $@) .)


$(INTEL_LIVEIMAGE_TARGET): \
		$(INTEL_PATH_BUILD)/tasks/liveimage.mk \
		$(liveimage_zip) \
		$(MKDOSFS) \
		$(MCOPY) \
                $(live_bootimage) \
		$(INTEL_PATH_BUILD)/bootloader_from_zip \

	$(hide) $(INTEL_PATH_BUILD)/bootloader_from_zip \
		--fastboot $(live_bootimage) \
		--zipfile $(liveimage_zip) \
                --bootable \
                $@

.PHONY: liveimage
liveimage: $(INTEL_LIVEIMAGE_TARGET)
	$(warning USE OF THE LIVE IMAGE IS UNSUPPORTED - YOU WILL NEED TO WORK THROUGH BUGS ON YOUR OWN!)

endif # ifeq (liveimage,$(LIVEIMAGE_GOAL))
