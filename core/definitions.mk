# Base directory for our Makefiles.
IAFW_BUILD_SYSTEM := $(INTEL_PATH_BUILD)/core

# Used in Android.mk to produce a binary
BUILD_EFI_STATIC_LIBRARY := $(IAFW_BUILD_SYSTEM)/iafw_static_library.mk
BUILD_IAFW_STATIC_LIBRARY := $(IAFW_BUILD_SYSTEM)/iafw_static_library.mk
BUILD_EFI_EXECUTABLE := $(IAFW_BUILD_SYSTEM)/efi_executable.mk
BUILD_SBL_EXECUTABLE := $(IAFW_BUILD_SYSTEM)/sbl_executable.mk

# Override default definition
CLEAR_VARS := $(IAFW_BUILD_SYSTEM)/clear_vars.mk

# Interesting binaries
FASTBOOT := $(HOST_OUT_EXECUTABLES)/fastboot
GENERATE_VERITY_KEY := $(HOST_OUT_EXECUTABLES)/generate_verity_key$(HOST_EXECUTABLE_SUFFIX)
OPENSSL := openssl
SBSIGN := sbsign
MKDOSFS := mkdosfs
#MKEXT2IMG := $(HOST_OUT_EXECUTABLES)/mkext2img
#DUMPEXT2IMG := $(HOST_OUT_EXECUTABLES)/dumpext2img
MCOPY := mcopy
SESL := sign-efi-sig-list$(HOST_EXECUTABLE_SUFFIX)
CTESL := cert-to-efi-sig-list$(HOST_EXECUTABLE_SUFFIX)
IASL := $(INTEL_PATH_BUILD)/acpi-tools/linux64/bin/iasl

# Generation
KF4SBL_SYMBOLS_ZIP := $(PRODUCT_OUT)/kf4sbl_symbols.zip
FB4SBL_SYMBOLS_ZIP := $(PRODUCT_OUT)/fb4sbl_symbols.zip

# Extra host tools we need built to use our *_from_target_files
# or sign_target_files_* scripts
INTEL_OTATOOLS := \
    $(GENERATE_VERITY_KEY) \
    $(AVBTOOL)

ifeq ($(KERNELFLINGER_SUPPORT_NON_EFI_BOOT),true)
# NON UEFI platform
INTEL_OTATOOLS += \
 #   $(MKEXT2IMG) \
 #  $(DUMPEXT2IMG) \
    $(FASTBOOT) \
    $(IASL)
endif

ifeq ($(BOARD_USE_SBL),true)
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
	-D_FORTIFY_SOURCE=2 \
	-Wa,--noexecstack \
	-Werror=format-security

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
TARGET_SBL_LDS := $(IAFW_BUILD_SYSTEM)/elf_$(TARGET_IAFW_ARCH_NAME)_sbl.lds
TARGET_IAFW_GLOBAL_OBJCOPY_FLAGS := \
	-j .text -j .sdata -j .data \
	-j .dynamic -j .dynsym  -j .rel \
	-j .rela -j .rela.dyn -j .reloc -j .eh_frame

IAFW_TOOLCHAIN_GCC_ROOT := prebuilts/gcc/$(HOST_PREBUILT_TAG)/x86/x86_64-linux-android-$(TARGET_GCC_VERSION)
IAFW_TOOLCHAIN_CLANG_ROOT := $(LLVM_PREBUILTS_PATH)
IAFW_TOOLS_GCC_PREFIX := $(IAFW_TOOLCHAIN_GCC_ROOT)/bin/x86_64-linux-android-
IAFW_TOOLS_CLANG_PREFIX := $(IAFW_TOOLCHAIN_CLANG_ROOT)
IAFW_STRIP := $(IAFW_TOOLS_GCC_PREFIX)strip$(HOST_EXECUTABLE_SUFFIX)
IAFW_LD := $(IAFW_TOOLS_GCC_PREFIX)ld.bfd$(HOST_EXECUTABLE_SUFFIX)
IAFW_CC := $(IAFW_TOOLS_CLANG_PREFIX)/clang
IAFW_OBJCOPY := $(IAFW_TOOLS_GCC_PREFIX)objcopy$(HOST_EXECUTABLE_SUFFIX)
EFI_OBJCOPY := $(IAFW_OBJCOPY)
ifeq ($(TARGET_IAFW_ARCH),x86_64)
IAFW_LIBCLANG := $(IAFW_TOOLCHAIN_CLANG_ROOT)/../lib64/clang/12.0.7/lib/linux/libclang_rt.builtins-x86_64-android.a
else
IAFW_LIBCLANG := $(IAFW_TOOLCHAIN_CLANG_ROOT)/../lib64/clang/12.0.7/lib/linux/libclang_rt.builtins-i686-android.a
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

define transform-o-to-sbl-executable
@echo "target SBL Executable: $(PRIVATE_MODULE) ($@)"
$(hide) mkdir -p $(dir $@)
$(hide) $(IAFW_LD) $1 \
    --defsym=CONFIG_LP_BASE_ADDRESS=$(LIBPAYLOAD_BASE_ADDRESS) \
    --defsym=CONFIG_LP_HEAP_SIZE=$(LIBPAYLOAD_HEAP_SIZE) \
    --defsym=CONFIG_LP_STACK_SIZE=$(LIBPAYLOAD_STACK_SIZE) \
    --whole-archive $(call module-built-files,$(LIBPAYLOAD_CRT0)) --no-whole-archive \
    $(PRIVATE_ALL_OBJECTS) --start-group $(PRIVATE_ALL_STATIC_LIBRARIES) --end-group $(IAFW_LIBCLANG) \
    -Map $(@:.sbl=.map) -o $(@:.sbl=.sym.elf)
$(hide)$(IAFW_STRIP) --strip-all $(@:.sbl=.sym.elf) -o $(@:.sbl=.elf)

$(hide) cp $(@:.sbl=.elf) $@

$(eval SBL_DIR := $(dir $@))
$(hide)rm -rf $(SBL_DIR)/cmdline1
$(hide)touch $(SBL_DIR)/cmdline1
python3 $(INTEL_PATH_BUILD)/containertool/GenContainer.py create -t MULTIBOOT -cl CMD1:$(SBL_DIR)/cmdline1 \
ELF1:$@ -k $(INTEL_PATH_BUILD)/testkeys/OS1_TestKey_Priv_RSA3072.pem -o $(SBL_DIR)/sbl_bm

if [ $(findstring kf4sbl,$(PRIVATE_MODULE) ) ]; then \
	cp $(SBL_DIR)/sbl_bm $(PRODUCT_OUT)/sbl_bm; \
elif [ $(findstring fb4sbl,$(PRIVATE_MODULE) ) ]; then \
	cp $(SBL_DIR)/sbl_bm $(PRODUCT_OUT)/sbl_fb; \
fi

if [ $(findstring true, $(ACRN_HV)) ]; then \
if [ $(findstring kf4sbl,$(PRIVATE_MODULE) ) ]; then \
	rm -rf $(SBL_DIR)/cmdline-acrn; \
	rm -rf $(SBL_DIR)/cmdline-kf; \
	rm -rf $(SBL_DIR)/acrn.32.out; \
	echo -ne "serail_baseaddr=0x3f8 serail_type=1 serail_regwidth=1\0" > $(SBL_DIR)/cmdline-acrn; \
	echo -ne "kernelflinger\0" > $(SBL_DIR)/cmdline-kf; \
	cp $(TOP)/vendor/intel/acrn/sample_a/acrn.32.out $(SBL_DIR)/acrn.32.out; \
if [ $(findstring optee,$(TEE) ) ]; then \
	rm -rf $(SBL_DIR)/cmdline-tee; \
	rm -rf $(SBL_DIR)/tee.elf; \
	echo -ne "tee_elf\0" > $(SBL_DIR)/cmdline-tee; \
	cp $(TOP)/vendor/intel/optee/optee_release_binaries/release/tee.elf $(SBL_DIR)/tee.elf; \
	python3 $(INTEL_PATH_BUILD)/containertool/GenContainer.py create -t MULTIBOOT \
        -cl CMD1:$(SBL_DIR)/cmdline-acrn ELF1:$(SBL_DIR)/acrn.32.out CMD2:$(SBL_DIR)/cmdline-kf ELF2:$@ \
        CMD3:$(SBL_DIR)/cmdline-tee ELF3:$(SBL_DIR)/tee.elf \
        -k $(INTEL_PATH_BUILD)/testkeys/OS1_TestKey_Priv_RSA3072.pem -o $(PRODUCT_OUT)/sbl_acrn; \
else \
	python3 $(INTEL_PATH_BUILD)/containertool/GenContainer.py create -t MULTIBOOT \
	-cl CMD1:$(SBL_DIR)/cmdline-acrn ELF1:$(SBL_DIR)/acrn.32.out CMD2:$(SBL_DIR)/cmdline-kf ELF2:$@ \
	-k $(INTEL_PATH_BUILD)/testkeys/OS1_TestKey_Priv_RSA3072.pem -o $(PRODUCT_OUT)/sbl_acrn; \
	python3 $(INTEL_PATH_BUILD)/containertool/GenContainer.py create -t MULTIBOOT \
	-cl CMD1:$(SBL_DIR)/cmdline-acrn ELF1:$(SBL_DIR)/acrn.32.out \
	-k $(INTEL_PATH_BUILD)/testkeys/OS1_TestKey_Priv_RSA3072.pem -o $(PRODUCT_OUT)/sbl_mod_acrn; \
	python3 $(INTEL_PATH_BUILD)/containertool/GenContainer.py create -t MULTIBOOT_MODULE \
	-cl CMD2:$(SBL_DIR)/cmdline-kf ELF2:$@ \
	-k $(INTEL_PATH_BUILD)/testkeys/OS1_TestKey_Priv_RSA3072.pem -o $(PRODUCT_OUT)/sbl_mod_kf; \
fi \
fi \
fi

$(hide) if [ "$(PRIVATE_MODULE:debug=)" = fb4sbl-user ]; then \
	zip -juy $(FB4SBL_SYMBOLS_ZIP) $(@:.sbl=.map) $(@:.sbl=.sym.elf); \
	zip -juy $(FB4SBL_SYMBOLS_ZIP) $@; \
elif [ "$(PRIVATE_MODULE:debug=)" = kf4sbl-user ]; then \
	zip -juy $(KF4SBL_SYMBOLS_ZIP) $(@:.sbl=.map) $(@:.sbl=.sym.elf); \
fi
endef

# Hook up the prebuilts generation mechanism
include $(INTEL_PATH_COMMON)/external/external.mk

# Hook to check all modules
BUILD_NOTICE_FILE := $(INTEL_PATH_COMMON)/notice_files.mk
