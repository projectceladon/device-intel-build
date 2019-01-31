ifeq ($(BOARD_HAS_USB_DISK),true)

ifeq ($(FLASHFILE_VARIANTS),)
# 0x7e0000 is multiple of sectors/track(32 or 63), avoid mtools check error.
$(BOARD_USB_DISK_IMAGES): fast_flashfiles $(MKDOSFS) $(MCOPY)
	$(hide) rm -f $@ && $(MKDOSFS) -n UDISK -C $@ 0x7e0000
	$(hide) $(MCOPY) -Q -i $@ $(FAST_FLASHFILES_DIR)/* ::
else
$(BOARD_USB_DISK_IMAGES): fast_flashfiles $(MKDOSFS) $(MCOPY)
	for variant in $(FLASHFILE_VARIANTS); do \
		eval "usb_disk$${variant}_files=(`ls $(FAST_FLASHFILES_DIR)/*_$${variant}*`)"; \
	done; \
	usb_disk_files=(`ls $(FAST_FLASHFILES_DIR)/*`); \
	usb_disk_common_files=(); \
	for file in $${usb_disk_files[@]}; do \
		match=false; \
		for variant in $(FLASHFILE_VARIANTS); do \
			name=usb_disk$${variant}_files[*]; \
			grep -q " $${file} " <<< " $${!name} " && match=true && break; \
		done; \
		$${match} && continue; \
		usb_disk_common_files+=($${file}); \
	done; \
	for variant in $(FLASHFILE_VARIANTS); do \
		name=usb_disk$${variant}_files[@]; \
		rm -f $(BOARD_USB_DISK_IMAGE_PFX)-$${variant}.img; \
		$(MKDOSFS) -n UDISK -C $(BOARD_USB_DISK_IMAGE_PFX)-$${variant}.img 0x7e0000; \
		$(MCOPY) -Q -i $(BOARD_USB_DISK_IMAGE_PFX)-$${variant}.img $(FAST_FLASHFILES_DIR)/installer_$${variant}.cmd ::installer.cmd; \
		$(MCOPY) -Q -i $(BOARD_USB_DISK_IMAGE_PFX)-$${variant}.img $${usb_disk_common_files[@]} $${!name} ::; \
	done;
endif

flashfiles: $(BOARD_USB_DISK_IMAGES)

publish_usb_disk_image: $(BOARD_USB_DISK_IMAGES) publish_mkdir_dest
	for image in $(BOARD_USB_DISK_IMAGES); do \
		$(INTEL_PATH_BUILD)/createcraffimage.py --image $${image}; \
		$(ACP) $${image/.img/.craff} $(publish_dest); \
	done

publish_ci: publish_usb_disk_image

endif # BOARD_USB_DISK_IMAGES
