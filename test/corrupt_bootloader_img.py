#!/usr/bin/env python
#
"""
Corrupt data section & signed section of kf4abl binary from bootloader.img binary.

Usage: corrupt_bootloader_img.py <input_bootloader_source_image>

Author: xiangx.deng@intel.com

"""

import sys
import struct
import argparse
import shutil
import os
import subprocess

from sys import exit, stderr
from argparse import ArgumentParser

if sys.hexversion < 0x02070000:
    print >> sys.stderr, "Python 2.7 or newer is required."
    sys.exit(1)

sign_filename = "bootloader_corrupted_signature"
data_filename = "bootloader_corrupted_data"

crc_len = 4
sign_len = 256
ran_sz = 16
osloader_offset = 16384 * 1024
old_strings = 'efiwrapper library initialization failed'
new_strings = 'failed library efiwrapper initialization'

def corrupt_data_section(out_f):
    """
      corrupt data section of iasimage with specified strings
    """
    subprocess.check_output(["sed", "-i", "s/%s/%s/g" % (old_strings, new_strings), out_f])

def corrupt_signature_section(out_f):
    """
      corrupt signature section of iasimage with random number
    """
    #get the abl binary from the in_f
    #the method is to get the payload offset plus
    #palyload length plus the crc checksum
    s = struct.Struct('I I I I I I I')
    with open(out_f, "rb+") as fh:
        fh.seek(osloader_offset, 0)
        u = s.unpack(fh.read(struct.calcsize(s.format)))
        data_len = u[3]
        data_off = u[4]
        print('get fh data_len = %d  data_off = %x' % (data_len, data_off))
        unsigned_len = data_off + data_len + crc_len
        sign_off = ((unsigned_len + sign_len - 1) // sign_len) * sign_len
        print('unsigned_len = %d  sign_off = %x' % (unsigned_len, sign_off))
        fh.seek(osloader_offset + sign_off, 0)
        random_str = open('/dev/random').read(ran_sz)
        # print("get random string = %s" % random_str)
        fh.write(random_str)
        fh.close()

def main():
    parser = argparse.ArgumentParser(description='corrupt data&signature section of iasimage')
    parser.add_argument('filename', type=str, help='filename, e.g. bootloader_gr_mrb_b1')
    args = parser.parse_args()

    print "entering corrupt process"
    in_f = args.filename
    bootloader_path = os.path.dirname(os.path.abspath(args.filename))
    # corrupt data section
    out_f = os.path.join(bootloader_path, data_filename)
    shutil.copy2(in_f, out_f)
    corrupt_data_section(out_f)
    print "bootloader corrupt data section done!"
    # corrupt signature section
    out_f = os.path.join(bootloader_path, sign_filename)
    shutil.copy2(in_f, out_f)
    corrupt_signature_section(out_f)
    print "bootloader corrupt sign section done!"

if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        print
        print "   ERROR: %s" % (e,)
        print
        sys.exit(1)

