# Base directory for our Makefiles.
EFI_BUILD_SYSTEM := device/intel/build/core

# Used in Android.mk to produce a binary
BUILD_EFI_STATIC_LIBRARY := $(EFI_BUILD_SYSTEM)/efi_static_library.mk
BUILD_EFI_EXECUTABLE := $(EFI_BUILD_SYSTEM)/efi_executable.mk

# Override default definition
CLEAR_VARS := $(EFI_BUILD_SYSTEM)/clear_vars.mk

# Interesting binaries
KEYSTORE_SIGNER := $(HOST_OUT_EXECUTABLES)/keystore_signer
OPENSSL := $(HOST_OUT_EXECUTABLES)/openssl$(HOST_EXECUTABLE_SUFFIX)
SBSIGN := $(HOST_OUT_EXECUTABLES)/sbsign$(HOST_EXECUTABLE_SUFFIX)

# Extra host tools we need built to use our *_from_target_files
# or sign_target_files_* scripts
INTEL_OTATOOLS := \
    $(SBSIGN) \
    $(KEYSTORE_SIGNER)

otatools: $(INTEL_OTATOOLS)

# FIXME: may be unsafe to omit -no-sse
TARGET_EFI_GLOBAL_CFLAGS := -ggdb -O3 -fno-stack-protector \
	-fno-strict-aliasing -fpic \
	-fshort-wchar -mno-red-zone -maccumulate-outgoing-args \
	-mno-mmx -fno-builtin -fno-tree-loop-distribute-patterns \
	-ffreestanding -fno-stack-check

TARGET_EFI_GLOBAL_LDFLAGS := -nostdlib --warn-common --no-undefined \
	--fatal-warnings -shared -Bsymbolic -znocombreloc

GNU_EFI_CRT0 := $(call intermediates-dir-for,STATIC_LIBRARIES,crt0-efi)/crt0-efi.o
GNU_EFI_BASE := external/gnu-efi/gnu-efi-3.0/gnuefi

ifeq ($(TARGET_UEFI_ARCH),x86_64)
    TARGET_EFI_GLOBAL_CFLAGS += -DEFI_FUNCTION_WRAPPER -DGNU_EFI_USE_MS_ABI
    TARGET_EFI_ARCH_NAME := x86_64
else
    TARGET_EFI_GLOBAL_CFLAGS += -m32
    TARGET_EFI_ARCH_NAME := ia32
endif

TARGET_EFI_GLOBAL_LDFLAGS += -T $(GNU_EFI_BASE)/elf_$(TARGET_EFI_ARCH_NAME)_efi.lds
TARGET_EFI_GLOBAL_OBJCOPY_FLAGS := \
	-j .text -j .sdata -j .data \
	-j .dynamic -j .dynsym  -j .rel \
	-j .rela -j .rela.dyn -j .reloc -j .eh_frame

EFI_TOOLCHAIN_ROOT := prebuilts/gcc/$(HOST_PREBUILT_TAG)/x86/x86_64-linux-android-$(TARGET_GCC_VERSION)
EFI_TOOLS_PREFIX := $(EFI_TOOLCHAIN_ROOT)/bin/x86_64-linux-android-
EFI_LD := $(EFI_TOOLS_PREFIX)ld$(HOST_EXECUTABLE_SUFFIX)
EFI_CC := $(EFI_TOOLS_PREFIX)gcc$(HOST_EXECUTABLE_SUFFIX)
EFI_OBJCOPY := $(EFI_TOOLS_PREFIX)objcopy$(HOST_EXECUTABLE_SUFFIX)
EFI_LIBGCC := $(shell $(EFI_CC) $(TARGET_EFI_GLOBAL_CFLAGS) -print-libgcc-file-name)

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

define transform-verity-key-to-cert
@echo "Verity DER certificate:  $(notdir $@) <= $(notdir $<)"
$(hide) mkdir -p $(dir $@)
$(hide) $(OPENSSL) rsa -pubout -inform PEM -outform DER -in $< -out $@
endef

define transform-o-to-efi-executable
@echo "target EFI Executable: $(PRIVATE_MODULE) ($@)"
$(hide) mkdir -p $(dir $@)
$(hide) $(EFI_LD) $(PRIVATE_LDFLAGS) \
    $(GNU_EFI_CRT0) $(PRIVATE_ALL_OBJECTS) --start-group $(PRIVATE_ALL_STATIC_LIBRARIES) --end-group $(EFI_LIBGCC) \
    -o $(@:.efi=.so)
$(hide) $(EFI_OBJCOPY) $(PRIVATE_OBJCOPY_FLAGS) \
    --target=efi-app-$(TARGET_EFI_ARCH_NAME) $(@:.efi=.so) $(@:.efi=.efiunsigned)
$(hide) $(SBSIGN) --key $1 --cert $2 --output $@ $(@:.efi=.efiunsigned)
endef

