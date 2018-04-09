# Base directory for our Makefiles.
IAFW_BUILD_SYSTEM := device/intel/build/core

# Used in Android.mk to produce a binary
BUILD_EFI_STATIC_LIBRARY := $(IAFW_BUILD_SYSTEM)/iafw_static_library.mk
BUILD_IAFW_STATIC_LIBRARY := $(IAFW_BUILD_SYSTEM)/iafw_static_library.mk
BUILD_EFI_EXECUTABLE := $(IAFW_BUILD_SYSTEM)/efi_executable.mk
BUILD_ABL_EXECUTABLE := $(IAFW_BUILD_SYSTEM)/abl_executable.mk

# Override default definition
CLEAR_VARS := $(IAFW_BUILD_SYSTEM)/clear_vars.mk

# Interesting binaries
GENERATE_VERITY_KEY := $(HOST_OUT_EXECUTABLES)/generate_verity_key$(HOST_EXECUTABLE_SUFFIX)
MCOPY := $(HOST_OUT_EXECUTABLES)/mcopy$(HOST_EXECUTABLE_SUFFIX)
SESL :=  $(HOST_OUT_EXECUTABLES)/sign-efi-sig-list$(HOST_EXECUTABLE_SUFFIX)
CTESL :=  $(HOST_OUT_EXECUTABLES)/cert-to-efi-sig-list$(HOST_EXECUTABLE_SUFFIX)
OPENSSL := openssl
MKDOSFS := mkdosfs
SBSIGN := sbsign

# Extra host tools we need built to use our *_from_target_files
# or sign_target_files_* scripts
INTEL_OTATOOLS := \
    $(GENERATE_VERITY_KEY) \
    $(SESL) \
    $(CTESL)

otatools: $(INTEL_OTATOOLS)

# FIXME: may be unsafe to omit -no-sse
TARGET_IAFW_GLOBAL_CFLAGS := -ggdb -O3 -fno-stack-protector \
	-fno-strict-aliasing -fpic \
	-fshort-wchar -mno-red-zone -maccumulate-outgoing-args \
	-mno-mmx -fno-builtin -fno-tree-loop-distribute-patterns \
	-ffreestanding -fno-stack-check

TARGET_IAFW_GLOBAL_LDFLAGS := -nostdlib --no-undefined \
	--fatal-warnings -Bsymbolic -znocombreloc

ifneq ($(TARGET_UEFI_ARCH),)
    TARGET_IAFW_ARCH := $(TARGET_UEFI_ARCH)
endif

ifeq ($(TARGET_IAFW_ARCH),x86_64)
    TARGET_IAFW_GLOBAL_CFLAGS += -DEFI_FUNCTION_WRAPPER -DGNU_EFI_USE_MS_ABI
    TARGET_IAFW_ARCH_NAME := x86_64
    TARGET_EFI_ARCH_NAME := $(TARGET_IAFW_ARCH_NAME)
else
    TARGET_IAFW_GLOBAL_CFLAGS += -m32
    TARGET_IAFW_ARCH_NAME := ia32
    TARGET_EFI_ARCH_NAME := $(TARGET_IAFW_ARCH_NAME)
    TARGET_IAFW_ASFLAGS := -m32
endif

GNU_EFI_CRT0 := crt0-efi-$(TARGET_IAFW_ARCH_NAME)
LIBPAYLOAD_CRT0 := crt0-libpayload-$(TARGET_IAFW_ARCH_NAME)

TARGET_EFI_LDS := $(IAFW_BUILD_SYSTEM)/elf_$(TARGET_IAFW_ARCH_NAME)_efi.lds
TARGET_ABL_LDS := $(IAFW_BUILD_SYSTEM)/elf_$(TARGET_IAFW_ARCH_NAME)_abl.lds
TARGET_IAFW_GLOBAL_OBJCOPY_FLAGS := \
	-j .text -j .sdata -j .data \
	-j .dynamic -j .dynsym  -j .rel \
	-j .rela -j .rela.dyn -j .reloc -j .eh_frame

IAFW_TOOLCHAIN_ROOT := prebuilts/gcc/$(HOST_PREBUILT_TAG)/x86/x86_64-linux-android-$(TARGET_GCC_VERSION)
IAFW_TOOLS_PREFIX := $(IAFW_TOOLCHAIN_ROOT)/bin/x86_64-linux-android-
IAFW_STRIP := $(IAFW_TOOLS_PREFIX)strip$(HOST_EXECUTABLE_SUFFIX)
IAFW_LD := $(IAFW_TOOLS_PREFIX)ld.bfd$(HOST_EXECUTABLE_SUFFIX)
IAFW_CC := $(IAFW_TOOLS_PREFIX)gcc$(HOST_EXECUTABLE_SUFFIX)
IAFW_OBJCOPY := $(IAFW_TOOLS_PREFIX)objcopy$(HOST_EXECUTABLE_SUFFIX)
EFI_OBJCOPY := $(IAFW_OBJCOPY)
IAFW_LIBGCC := $(shell $(IAFW_CC) $(TARGET_IAFW_GLOBAL_CFLAGS) -print-libgcc-file-name)

# Transformation definitions, ala build system's definitions.mk

define transform-der-key-to-pem-key
@echo "PEM key: $(notdir $@) <= $(notdir $<)"
$(hide) mkdir -p $(dir $@)
$(hide) $(OPENSSL) pkcs8 -inform DER -outform PEM -nocrypt -in $< -out $@
endef

define transform-pem-cert-to-der-cert
@echo "DER cert: $(notdir $@) <= $(notdir $<)"
$(hide) mkdir -p $(dir $@)
$(hide) $(OPENSSL) x509 -inform PEM -outform DER -in $< -out $@
endef

define pad-binary
@echo "Padding to $(strip $1) bytes: $(notdir $@) <= $(notdir $<)"
$(hide) mkdir -p $(dir $@)
$(hide) dd ibs=$(strip $1) if=$< of=$@ count=1 conv=sync
endef

define transform-o-to-efi-executable
@echo "target EFI Executable: $(PRIVATE_MODULE) ($@)"
$(hide) mkdir -p $(dir $@)
$(hide) $(IAFW_LD) $(PRIVATE_LDFLAGS) \
    --whole-archive $(call module-built-files,$(GNU_EFI_CRT0)) --no-whole-archive \
    $(PRIVATE_ALL_OBJECTS) --start-group $(PRIVATE_ALL_STATIC_LIBRARIES) --end-group $(IAFW_LIBGCC) \
    -o $(@:.efi=.so)
$(hide) $(IAFW_OBJCOPY) $(PRIVATE_OBJCOPY_FLAGS) \
    --target=efi-app-$(TARGET_IAFW_ARCH_NAME) $(@:.efi=.so) $(@:.efi=.efiunsigned)
$(hide) $(SBSIGN) --key $1 --cert $2 --output $@ $(@:.efi=.efiunsigned)
endef

define transform-o-to-abl-executable
@echo "target ABL Executable: $(PRIVATE_MODULE) ($@)"
$(hide) mkdir -p $(dir $@)
$(hide) $(IAFW_LD) $(PRIVATE_LDFLAGS) \
    --defsym=CONFIG_LP_BASE_ADDRESS=$(LIBPAYLOAD_BASE_ADDRESS) \
    --defsym=CONFIG_LP_HEAP_SIZE=$(LIBPAYLOAD_HEAP_SIZE) \
    --defsym=CONFIG_LP_STACK_SIZE=$(LIBPAYLOAD_STACK_SIZE) \
    --whole-archive $(call module-built-files,$(LIBPAYLOAD_CRT0)) --no-whole-archive \
    $(PRIVATE_ALL_OBJECTS) --start-group $(PRIVATE_ALL_STATIC_LIBRARIES) --end-group $(IAFW_LIBGCC) \
    -o $(@:.abl=.elf)
$(hide) if `test $(TARGET_BUILD_VARIANT) == user`; then $(IAFW_STRIP) -s $(@:.abl=.elf) ; fi
$(hide) $(ABLIMAGE) -o $(@:.abl=.ablunsigned) -i 0x40000 $(@:.abl=.elf)
$(hide) if `test $(TARGET_BUILD_VARIANT) == eng`; then \
	cp $(@:.abl=.ablunsigned) $@ ; else \
	$(ABLSIGN) $(@:.abl=.ablunsigned) \
	$(PRODUCTS.$(INTERNAL_PRODUCT).PRODUCT_VERITY_SIGNING_KEY).pk8 \
	$(PRODUCTS.$(INTERNAL_PRODUCT).PRODUCT_VERITY_SIGNING_KEY).x509.pem \
	$@ ; fi
endef

# Hook up the prebuilts generation mechanism
#include device/intel/common/external/external.mk

# Hook to check all modules
#BUILD_NOTICE_FILE := device/intel/common/notice_files.mk
