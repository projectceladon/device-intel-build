ifneq ($(NON_GMIN_BUILD),true)
count = $(shell echo -n $(TARGET_PRODUCT) | wc -m)
evaluate = $(shell bash -c '[ "$(count)" -gt "22" ] && echo true')
ifeq ($(evaluate), true)
$(error TARGET_PRODUCT=$(TARGET_PRODUCT) has $(count) characters; must not exceed 11)
endif
endif
