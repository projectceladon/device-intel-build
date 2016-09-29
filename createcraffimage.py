#!/usr/bin/env python

# Copyright (c) 2014, Intel Corporation.
# Author: Jackie, Fu <yonghuax.fu@intel.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms and conditions of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.

import sys
import os
import md5
import os.path
import shutil

"""
Script to create a Craff image or to show information it contains.
"""

from sys import version_info

if version_info < (2, 7, 3):
    exit('Python version must be 2.7.3 or higher')

from logging import (debug, info, error, DEBUG, INFO, getLogger, basicConfig)
from argparse import ArgumentParser
from os import remove, stat
from os.path import isfile, normcase, normpath, realpath
from struct import unpack, pack
from uuid import UUID, uuid4
from binascii import crc32
from re import compile as re_compile
from collections import namedtuple
from ConfigParser import SafeConfigParser, ParsingError, NoOptionError
from math import floor, log

def usage():
    """
    Used to make main args parser and helper
    """
    cmdparser = ArgumentParser(description=__doc__)

    cmdparser.add_argument('FILE', type=str,
                           help=('The path of craff image.'))
    cmds_group = cmdparser.add_mutually_exclusive_group()

    cmds_group.add_argument('--image', action='store_true',
                            help='Command to create a new craff image.')
    create_group = cmdparser.add_argument_group('image')

    return cmdparser

def find_path_file(file_path):
    """
    find the path of the file
    """
    if os.path.isdir(file_path):
        return file_path
    elif os.path.isfile(file_path):
        return os.path.dirname(file_path)

def cur_file_dir():
    """
    Get the current path of the script
    """
    path = sys.path[0]
    if os.path.isdir(path):
        return path
    elif os.path.isfile(path):
        return os.path.dirname(path)

def get_the_file_name(filenames):
   """
   Only get the file name
   """
   file_name=[]
   if "." in filenames:
      filename = filenames.split(".")
      file_name.append(filename)
   print file_name[0][0]
   print file_name[0][1]
   return file_name[0][0]

def craffimg(img_path):
    """
    Create the craff image
    """
    scriptpath = cur_file_dir()
    tool = scriptpath + '/simics-tools/bin/craff'
    print img_path
    name = os.path.basename(img_path)
    onlyname = get_the_file_name(name)
    print onlyname
    toolpath = tool + ' -o ' + onlyname + '.craff ' + img_path
    filepath = find_path_file(img_path)
    os.popen(toolpath).read()
    craffname = onlyname + '.craff'
    crafffilepath = filepath + '/' + craffname
    print crafffilepath
    if os.path.isfile(crafffilepath):
         os.remove(crafffilepath)
    shutil.move(craffname,filepath)

def main():
    """
    main function used to create craff image.
    """
    cmdargs = usage().parse_args()
    logger = getLogger()
    basicConfig(format=' %(levelname)s %(message)s')
    img_path = realpath(normpath(normcase(cmdargs.FILE)))
    craffimg(img_path)
    exit(0)


if __name__ == '__main__':
        main()
