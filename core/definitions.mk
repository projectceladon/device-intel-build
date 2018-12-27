# Base directory for our Makefiles.
IAFW_BUILD_SYSTEM := $(INTEL_PATH_BUILD)/core

# Used in Android.mk to produce a binary
BUILD_EFI_STATIC_LIBRARY := $(IAFW_BUILD_SYSTEM)/iafw_static_library.mk
BUILD_IAFW_STATIC_LIBRARY := $(IAFW_BUILD_SYSTEM)/iafw_static_library.mk
BUILD_EFI_EXECUTABLE := $(IAFW_BUILD_SYSTEM)/efi_executable.mk
BUILD_ABL_EXECUTABLE := $(IAFW_BUILD_SYSTEM)/abl_executable.mk

# Override default definition
CLEAR_VARS := $(IAFW_BUILD_SYSTEM)/clear_vars.mk

# Interesting binaries
FASTBOOT := $(HOST_OUT_EXECUTABLES)/fastboot
GENERATE_VERITY_KEY := $(HOST_OUT_EXECUTABLES)/generate_verity_key$(HOST_EXECUTABLE_SUFFIX)
OPENSSL := $(HOST_OUT_EXECUTABLES)/openssl$(HOST_EXECUTABLE_SUFFIX)
SBSIGN := sbsign
ABLIMAGE := $(HOST_OUT_EXECUTABLES)/ias_image_app$(HOST_EXECUTABLE_SUFFIX)
ABLSIGN := $(HOST_OUT_EXECUTABLES)/ias_image_signer$(HOST_EXECUTABLE_SUFFIX)
MKDOSFS := mkdosfs
MKEXT2IMG := $(HOST_OUT_EXECUTABLES)/mkext2img
DUMPEXT2IMG := $(HOST_OUT_EXECUTABLES)/dumpext2img
MCOPY := mcopy
SESL := sign-efi-sig-list$(HOST_EXECUTABLE_SUFFIX)
CTESL := cert-to-efi-sig-list$(HOST_EXECUTABLE_SUFFIX)
IASL := $(HOST_OUT_EXECUTABLES)/iasl

# Generation
KF4ABL_SYMBOLS_ZIP := $(PRODUCT_OUT)/kf4abl_symbols.zip
FB4ABL_SYMBOLS_ZIP := $(PRODUCT_OUT)/fb4abl_symbols.zip

# Extra host tools we need built to use our *_from_target_files
# or sign_target_files_* scripts
INTEL_OTATOOLS := \
    $(GENERATE_VERITY_KEY) \
    $(AVBTOOL)

ifeq ($(KERNELFLINGER_SUPPORT_NON_EFI_BOOT),true)
# NON UEFI platform
INTEL_OTATOOLS += \
    $(ABLIMAGE) \
    $(ABLSIGN) \
    $(MKEXT2IMG) \
    $(DUMPEXT2IMG) \
    $(FASTBOOT) \
    $(IASL)
endif

ifeq ($(BOARD_FIRSTSTAGE_MOUNT_ENABLE),true)
    FIRST_STAGE_MOUNT_CFG_FILE := $(TARGET_DEVICE_DIR)/ablvars/asl/first-stage-mount-cfg.asl
else
    FIRST_STAGE_MOUNT_CFG_FILE := null
endif

ifeq ($(BOARD_USE_ABL),true)
INTEL_OTATOOLS += abl_toolchain
endif

otatools: $(INTEL_OTATOOLS)

# FIXME: may be unsafe to omit -no-sse
TARGET_IAFW_GLOBAL_CFLAGS := -ggdb -O3 -fstack-protector-strong \
	-fno-strict-aliasing -fpic \
	-fshort-wchar -mno-red-zone \
	-mno-mmx -fno-builtin \
	-m64 -mstackrealign \
	-mstack-alignment=32 \
	-ffreestanding -fno-stack-check \
	-Wno-pointer-sign \
	-Wno-address-of-packed-member \
	-Wno-macro-redefined \
	-Wno-pointer-bool-conversion \
	-Wno-unused-const-variable \
	-Wno-constant-conversion \
	-Wno-unused-function \
	-Wno-tautological-pointer-compare \
	-Wformat -Wformat-security \
	-D_FORTIFY_SOURCE=2

TARGET_IAFW_GLOBAL_LDFLAGS := -nostdlib --no-undefined \
	--fatal-warnings -Bsymbolic -znocombreloc -znoexecstack -zrelro -znow

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

IAFW_TOOLCHAIN_GCC_ROOT := prebuilts/gcc/$(HOST_PREBUILT_TAG)/x86/x86_64-linux-android-$(TARGET_GCC_VERSION)
IAFW_TOOLCHAIN_CLANG_ROOT := $(LLVM_PREBUILTS_PATH)
IAFW_TOOLS_GCC_PREFIX := $(IAFW_TOOLCHAIN_GCC_ROOT)/bin/x86_64-linux-android-
IAFW_TOOLS_CLANG_PREFIX := $(IAFW_TOOLCHAIN_CLANG_ROOT)
IAFW_LD := $(IAFW_TOOLS_GCC_PREFIX)ld.bfd$(HOST_EXECUTABLE_SUFFIX)
IAFW_CC := $(IAFW_TOOLS_CLANG_PREFIX)/clang
IAFW_OBJCOPY := $(IAFW_TOOLS_GCC_PREFIX)objcopy$(HOST_EXECUTABLE_SUFFIX)
EFI_OBJCOPY := $(IAFW_OBJCOPY)
ifeq ($(TARGET_IAFW_ARCH),x86_64)
IAFW_LIBCLANG := $(IAFW_TOOLCHAIN_CLANG_ROOT)/../lib64/clang/6.0.2/lib/linux/libclang_rt.builtins-x86_64-android.a
else
IAFW_LIBCLANG := $(IAFW_TOOLCHAIN_CLANG_ROOT)/../lib64/clang/6.0.2/lib/linux/libclang_rt.builtins-i686-android.a
endif

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
$(hide) $(IAFW_LD) $3 \
    --whole-archive $(call module-built-files,$(GNU_EFI_CRT0)) --no-whole-archive \
    $(PRIVATE_ALL_OBJECTS) --start-group $(PRIVATE_ALL_STATIC_LIBRARIES) --end-group $(IAFW_LIBCLANG) \
    -o $(@:.efi=.so)
$(hide) $(IAFW_OBJCOPY) $(PRIVATE_OBJCOPY_FLAGS) \
    --target=efi-app-$(TARGET_IAFW_ARCH_NAME) $(@:.efi=.so) $(@:.efi=.efiunsigned)
$(hide) $(SBSIGN) --key $1 --cert $2 --output $@ $(@:.efi=.efiunsigned)
endef

define transform-o-to-abl-executable
@echo "target ABL Executable: $(PRIVATE_MODULE) ($@)"
$(hide) mkdir -p $(dir $@)
$(hide) $(IAFW_LD) $1 \
    --defsym=CONFIG_LP_BASE_ADDRESS=$(LIBPAYLOAD_BASE_ADDRESS) \
    --defsym=CONFIG_LP_HEAP_SIZE=$(LIBPAYLOAD_HEAP_SIZE) \
    --defsym=CONFIG_LP_STACK_SIZE=$(LIBPAYLOAD_STACK_SIZE) \
    --whole-archive $(call module-built-files,$(LIBPAYLOAD_CRT0)) --no-whole-archive \
    $(PRIVATE_ALL_OBJECTS) --start-group $(PRIVATE_ALL_STATIC_LIBRARIES) --end-group $(IAFW_LIBCLANG) \
    -Map $(@:.abl=.map) --strip-all -o $(@:.abl=.elf)

$(hide) if [ -e $(TARGET_DEVICE_DIR)/ablvars/acpi_table ]; then \
            cp $(TARGET_DEVICE_DIR)/ablvars/acpi_table $(dir $@)/ -rf; \
        fi
$(hide) if [ -e $(FIRST_STAGE_MOUNT_CFG_FILE) ]; then \
            $(IASL) -p $(dir $@)/acpi_table/ssdt $(FIRST_STAGE_MOUNT_CFG_FILE); \
        elif [ -e $(dir $@)/acpi_table/ssdt.aml ]; then \
            rm $(dir $@)/acpi_table/ssdt.aml; \
        fi

$(hide) wait

$(hide) if [ -e $(dir $@)/acpi.tables ]; then \
            rm -rf $(dir $@)/acpi.tables; \
        fi
$(hide) find $(dir $@)/acpi_table -type f | while read file; do \
	detect_size=`od -j4 -N4 -An -t u4 $${file}`; \
	[ -z "$${detect_size}" ] && detect_size=0; \
	actual_size=`wc -c < $${file}`; \
	if [ $${detect_size} -eq $${actual_size} ]; then \
		echo ACPI table length match: $${file}; \
		printf "Signature: %s, Length: $${actual_size}\n" `head -c 4 $${file}`; \
		cat $${file} >> $(dir $@)/acpi.tables; \
	fi; \
done
$(hide) dd if=/dev/zero of=$(dir $@)/cmdline bs=512 count=1;
$(hide) if [ -s $(dir $@)/acpi.tables ];then \
	echo 8600b1ac | xxd -r -ps > $(dir $@)/acpi_tag; \
	$(ABLIMAGE) -o $(@:.abl=.ablunsigned) -i 0x40300 $(dir $@)/cmdline $(@:.abl=.elf) $(dir $@)/acpi_tag $(dir $@)/acpi.tables; else \
	$(ABLIMAGE) -o $(@:.abl=.ablunsigned) -i 0x40300 $(dir $@)/cmdline $(@:.abl=.elf); fi
	$(ABLSIGN) $(@:.abl=.ablunsigned) \
	$(ABL_OS_KERNEL_KEY).pk8 \
	$(ABL_OS_KERNEL_KEY).x509.pem \
	$@
$(hide) if [ "$(PRIVATE_MODULE)" == fb4abl-userdebug ]; then \
	zip -juy $(FB4ABL_SYMBOLS_ZIP) $(@:.abl=.map) $(@:.abl=.sym.elf); \
	zip -juy $(FB4ABL_SYMBOLS_ZIP) $@; \
elif [ "$(PRIVATE_MODULE)" == kf4abl-userdebug ]; then \
	zip -juy $(KF4ABL_SYMBOLS_ZIP) $(@:.abl=.map) $(@:.abl=.sym.elf); \
fi
endef

# Hook up the prebuilts generation mechanism
include $(INTEL_PATH_COMMON)/external/external.mk

# Hook to check all modules
BUILD_NOTICE_FILE := $(INTEL_PATH_COMMON)/notice_files.mk
