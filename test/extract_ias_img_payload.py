#!/usr/bin/python
import struct
import sys
# #define KPI_MAGIC_PATTERN   0x2E6B7069 // ".kpi"
# From kp_image.h
# struct kpi_header                 // a KP image generic header:
# {
#	uint32_t    magic_pattern;    // identifies structure (acts as valid flag)
#	uint32_t    image_type;       // image and compression type; values TBD
#	uint32_t    version;          // header version
#	uint32_t    data_length;      // size of payload (data) in image
#	uint32_t    data_offset;      // offset to payload data from header
#	uint32_t    uncompressed_len; // uncompresse data length
#	uint32_t    header_crc;       // CRC-32C over entire hheader
# };
#
# We do not need to read the whole header, we only need data_length
# data_offset
#
#                  [0] magic
#                  | [1] image_type
#                  | | [2] version
#                  | | | [3] data_length
#                  | | | | [4] data_offset
#                  | | | | | [5] uncompressed_len
#                  | | | | | | [6] header_crc
#                  | | | | | | |
#                  v v v v v v v
s = struct.Struct('I I I I I I I')
f = open(sys.argv[1], "rb")
u = s.unpack(f.read(struct.calcsize(s.format)))
data_len = u[3]
data_off = u[4]

# Write the payload to stdout
f.seek(data_off, 0)
sys.stdout.write(f.read(data_len))
f.close()
