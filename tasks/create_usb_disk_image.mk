ifdef BOARD_USB_DISK_IMAGE

# 0x1f8000 is multiple of sectors/track(32 or 63), avoid mtools check error.
$(BOARD_USB_DISK_IMAGE): fast_flashfiles $(MKDOSFS) $(MCOPY)
	$(hide) rm -f $@ && $(MKDOSFS) -n UDISK -C $@ 0x1f8000
	$(hide) $(MCOPY) -Q -i $@ $(FAST_FLASHFILES_DIR)/* ::

flashfiles: $(BOARD_USB_DISK_IMAGE)

publish_usb_disk_image: $(BOARD_USB_DISK_IMAGE) publish_mkdir_dest
	$(hide) $(INTEL_PATH_BUILD)/createcraffimage.py --image $<
	$(hide) $(ACP) $(<:.img=.craff) $(publish_dest)

publish_ci: publish_usb_disk_image

endif # BOARD_USB_DISK_IMAGE
