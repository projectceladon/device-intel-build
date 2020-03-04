#!/usr/bin/python
"""
Given a sparse system.img, produces an tuple which contains the following information
such as fec_supported, verity metadata offset, verity metadata size, verity hash offset, verity hash size.

Usage:  fec_parse_verity.py file offset len
        file: system image file name
        offset: the last sparse chunk offset in file
        len:    the last sparse chunk length
"""
import sys
import os
import struct

FEC_BLOCK_SZ=4096
FEC_MAGIC=0xFECFECFE
FEC_HEADER_SZ=28
FEC_VERITY_METADATA_SZ=32768

def getsize(filename):
    st = os.stat(filename)
    return st.st_size

def usage():
    print("usage: {0} <file> <offset> <len>".format(sys.argv[0]))

def parse_fec_verity_data(b_file,b_offset,b_len):
    """
    parse the fec verity data to give the verity metadata and verity hash data offset and length
    """
    f = open(b_file, 'rb')
    system_total_sz=getsize(b_file)
    #read the beginning FEC_HEADER_SZ bytes at last block
    f.seek(-FEC_BLOCK_SZ, 2)
    header_bin = f.read(FEC_HEADER_SZ)
    (magic, version, header_sz, roots, size, inp_size) = struct.unpack("<5IQ", header_bin)

    verity_metadata_len=FEC_VERITY_METADATA_SZ
    verity_metadata_offset=0

    verity_hash_offset=0
    verity_hash_len=0

    if magic == FEC_MAGIC:
        fec_supported = True

        verity_metadata_len=FEC_VERITY_METADATA_SZ
        verity_metadata_offset=system_total_sz-FEC_BLOCK_SZ-size-verity_metadata_len

        verity_hash_offset=b_offset
        verity_hash_len=int(b_len)-verity_metadata_len-size-FEC_BLOCK_SZ
    else:
        fec_supported = False

    return (fec_supported,verity_metadata_offset,verity_metadata_len,verity_hash_offset,verity_hash_len)


if __name__ == "__main__":
    if len(sys.argv) == 4:
        res = parse_fec_verity_data(sys.argv[1], sys.argv[2],sys.argv[3])
        if res[0]:
            print("1 {0} {1} {2} {3}".format(*res[1:]))
        else:
            print("0 {0} {1} {2} {3}".format(*res[1:]))
    else:
        usage()
        exit(-1)
