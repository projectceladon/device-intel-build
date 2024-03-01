#!/usr/bin/env python
## @ GenMbImage.py
# Tools to operate on an acrn multiboot image
#
# Copyright (c) 2024, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
##

import sys
import os
import argparse
import re
sys.dont_write_bytecode = True
from   ctypes import *

class IMAGE_HDR (Structure):
    _pack_ = 1
    _fields_ = [
        ('magic',        ARRAY(c_char, 8)),   # magic number
        ('header_version',      c_uint32),   # Header Version
        ('header_size',        c_uint32),   # Header size in byte
        ('mod_offset',   c_uint32),    # Module binary offset in this image
        ('mod_size',   c_uint32),    # Module binary size
        ('mod_align',   c_uint32),    # Module binary alignment requirement
        ('cmdline',   ARRAY(c_char, 4096)),    # Module cmdline
        ]

    def __new__(cls, buf = None):
        if buf is None:
            return Structure.__new__(cls)
        else:
            return cls.from_buffer_copy(buf)

class IMAGE ():
    def __init__(self, buf = None):
        if buf is None:
            self.header = IMAGE_HDR()
        else:
            self.header = IMAGE_HDR(buf)
        self.module = bytearray();

    def init_header(self, alignment, cmdline):
        self.header.magic = 'ACRNMB2\x00'.encode()
        self.header.header_version = 1
        self.header.header_size = sizeof(IMAGE_HDR)
        if alignment != (1 << (alignment.bit_length() - 1)):
            raise Exception ('Alignment (0x%x) should to be power of 2 !' % alignment)
        self.header.mod_align = alignment
        self.header.mod_offset = (self.header.header_size + alignment - 1) & ~(alignment - 1)
        self.header.cmdline = cmdline.encode()

    def set_module(self, file):
        self.module = bytearray(open(file, 'rb').read())
        self.header.mod_size = len(self.module)

    def get_data(self):
        # Prepare data buffer
        header = self.header
        data = bytearray(header)
        offset = header.mod_offset
        padding = b'\xff' *  (offset - len(data))
        data.extend(padding + self.module)
        offset = (len(data) + 4095) & ~4095
        padding = b'\xff' *  (offset - len(data))
        data.extend(padding)
        return data

def display_image(args):
    None

def create_image(args):
    out_file = os.path.abspath(args.out_path)
    image = IMAGE()
    image.init_header(args.align, args.cmdline)
    image.set_module(args.module)
    data = image.get_data()
    open (out_file, 'wb').write(data)

def extract_image(args):
    None

def main():
    parser = argparse.ArgumentParser()
    sub_parser = parser.add_subparsers(help='command')

    # Command for display
    cmd_display = sub_parser.add_parser('view', help='display an image')
    cmd_display.add_argument('-i', dest='image',  type=str, required=True, help='input image')
    cmd_display.set_defaults(func=display_image)

    # Command for create
    cmd_create = sub_parser.add_parser('create', help='create an image')
    cmd_create.add_argument('-a', dest='align',  type=int, default=0x1000, help='Image alignment required when load')
    cmd_create.add_argument('-o', dest='out_path',  type=str, required=True, help='Image output directory/file')
    cmd_create.add_argument('-c', dest='cmdline',  type=str, default='', help='Commnad line for this image')
    cmd_create.add_argument('-m', dest='module',  type=str, required=True, help='Module binary for this image')
    cmd_create.set_defaults(func=create_image)

    # Command for extract
    cmd_extract = sub_parser.add_parser('extract', help='extract an image')
    cmd_extract.add_argument('-i',  dest='image',  type=str, required=True, help='input image path')
    cmd_extract.add_argument('-o', dest='out_dir',  type=str, default='.', help='Output directory')
    cmd_extract.set_defaults(func=extract_image)

    # Parse arguments and run sub-command
    args = parser.parse_args()
    try:
        func = args.func
    except AttributeError:
        parser.error("too few arguments")

    func(args)

if __name__ == '__main__':
    sys.exit(main())
