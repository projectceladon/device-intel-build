#!/usr/bin/python
# Author : Leo Sartre <leox.sartre@intel.com>

import struct
import sys

# From bootimg.h
#
##define BOOT_MAGIC_SIZE 8
#struct boot_img_hdr
#{
#    uint8_t magic[BOOT_MAGIC_SIZE];
#
#    uint32_t kernel_size;  /* size in bytes */
#    uint32_t kernel_addr;  /* physical load addr */
#
#    uint32_t ramdisk_size; /* size in bytes */
#    uint32_t ramdisk_addr; /* physical load addr */
#
#    uint32_t second_size;  /* size in bytes */
#    uint32_t second_addr;  /* physical load addr */
#
#    uint32_t tags_addr;    /* physical addr for kernel tags */
#    uint32_t page_size;    /* flash page size we assume */
#    uint32_t unused[2];    /* future expansion: should be 0 */
#
#    uint8_t name[BOOT_NAME_SIZE]; /* asciiz product name */
#
#    uint8_t cmdline[BOOT_ARGS_SIZE];
#
#    uint32_t id[8]; /* timestamp / checksum / sha1 / etc */
#
#    /* Supplemental command line data; kept here to maintain
#     * binary compatibility with older versions of mkbootimg */
#    uint8_t extra_cmdline[BOOT_EXTRA_ARGS_SIZE];
#} __attribute__((packed));

# We do not need to read the whole header, we only need kernel_size,
# ramdisk_size, second_size and page_size
#
#                  [0-7] magic[BOOT_MAGIC_SIZE]
#                  |  [8] kernel_size
#                  |  | [9] kernel_addr
#                  |  | | [10] ramdisk_size
#                  |  | | | [11] ramdisk_addr
#                  |  | | | | [12] second_size
#                  |  | | | | | [13] second_addr
#                  |  | | | | | | [14] tags_addr
#                  |  | | | | | | | [15] page_size
#                  |  | | | | | | | |
#                  v  v v v v v v v v
s = struct.Struct('8B I I I I I I I I')
f = open(sys.argv[1], "rb")
u = s.unpack(f.read(struct.calcsize(s.format)))
kernelSize = u[8]
ramdskSize = u[10]
secondSize = u[12]
pageSize = u[15]

# Compute the length of the image.
# According to BootSIgnature.java
#
#  int length = pageSize // include the page aligned image header
#          + ((kernelSize + pageSize - 1) / pageSize) * pageSize
#          + ((ramdskSize + pageSize - 1) / pageSize) * pageSize
#          + ((secondSize + pageSize - 1) / pageSize) * pageSize;
#  length = ((length + pageSize - 1) / pageSize) * pageSize;

length = pageSize \
         + ((kernelSize + pageSize - 1) / pageSize) * pageSize \
         + ((ramdskSize + pageSize - 1) / pageSize) * pageSize \
         + ((secondSize + pageSize - 1) / pageSize) * pageSize
length = ((length + pageSize - 1) / pageSize) * pageSize

# Write the unsigned image to stdout
f.seek(0, 0)
sys.stdout.write(f.read(length))
f.close()
