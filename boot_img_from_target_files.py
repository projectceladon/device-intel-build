#!/usr/bin/env python
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Generates a boot image from target-files zip.

Usage:  boot_efi_from_target_files [flags] input_target_files_zip \
output_file

  -p  (--partition)  <string>
      Partition name within target files zip

"""

import sys

if sys.hexversion < 0x02040000:
    print >> sys.stderr, "Python 2.4 or newer is required."
    sys.exit(1)

import os
import shutil

# missing in Python 2.4 and before
if not hasattr(os, "SEEK_SET"):
    os.SEEK_SET = 0

# Android Release Tools
sys.path.append("build/tools/releasetools")
import common

OPTIONS = common.OPTIONS
OPTIONS.partition = "FASTBOOT"


def WriteFileToDest(img, dest):
    """Write common.File to destination"""
    fid = open(dest, 'w')
    fid.write(img.data)
    fid.flush()
    fid.close()
    return fid


def main(argv):

    def option_handler(o, a):
        if o in ("-p", "--partition"):
            OPTIONS.partition = a
        else:
            return False
        return True

    args = common.ParseOptions(argv, __doc__,
                               extra_opts="p:",
                               extra_long_opts=["partition="],
                               extra_option_handler=option_handler)

    if (len(args) != 2):
        common.Usage(__doc__)
        sys.exit(1)

    print "unzipping target-files..."
    OPTIONS.input_tmp, input_zip = common.UnzipTemp(args[0])
    OPTIONS.info_dict = common.LoadInfoDict(input_zip)

    # Get Boot Image
    print "creating %s" % args[1]
    img = common.GetBootableImage(os.path.basename(args[1]),
                                  os.path.basename(args[1]),
                                  OPTIONS.input_tmp,
                                  OPTIONS.partition)

    # Write Boot Image
    WriteFileToDest(img, args[1])

    print "cleaning up..."
    shutil.rmtree(OPTIONS.input_tmp)

    print "done."


if __name__ == '__main__':
    try:
        common.CloseInheritedPipes()
        main(sys.argv[1:])
    except common.ExternalError, e:
        print
        print "   ERROR: %s" % (e,)
        print
        sys.exit(1)
