#!/usr/bin/env python
#
# Copyright (C) 2016 The Android Open Source Project
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
Re-sign ABL related binaries found in RADIO/provdata.zip with production
keys.
Usage: sign_target_files_abl <options> <input_target_files_zip> <output_file>
  -K  (--oem-key) <path to new keypair>
      Replace the OEM key inside kernelflinger with the replacement copy.
      The OEM keystore must be signed with this key.
      Expects a key pair assuming private key ends in .pk8 and public key
      with .x509.pem

  -I  (--ifwi-directory) <path>
      Path to the resigned IFWI, which is a directory contain all the resigned IFWI binaries.

  -V  (--variant) variant
  variant can be gr_mrb(A0) or gr_mrb_b1(B1)
"""

import sys
import shutil
import zipfile
import os
import os.path
import shlex
import tempfile
import subprocess
import struct
import json

if sys.hexversion < 0x02040000:
    print >> sys.stderr, "Python 2.4 or newer is required."
    sys.exit(1)

# Android Release Tools
sys.path.append("build/tools/releasetools")
import common

sys.path.append("device/intel/build/releasetools")
import intel_common

OPTIONS = common.OPTIONS
OPTIONS.ifwi_directory = ""
OPTIONS.variant = ""
OPTIONS.all_keys = set()
OPTIONS.oem_key = None
OPTIONS.target_product = None

crc_len = 4

def process_provzip(input_provzip, output_fn):
            path = "fastboot"
            dn = tempfile.mkdtemp()
            in_fname = input_provzip.extract(path, dn)
            process_iasimage(in_fname,output_fn)
            shutil.rmtree(dn)

def process_bootloader(in_f, out_f):
    d1 = tempfile.mkdtemp()
    cmd = ["dumpext2img"]
    cmd.append(in_f)
    cmd.append("osloader.bin")
    cmd.append(os.path.join(d1,"osloader.bin"))
    p = common.Run(cmd)
    p.wait()
    #assert p.returncode == 0, "dumpext2img failed: %d" % p.returncode
    process_iasimage(os.path.join(d1, "osloader.bin"), os.path.join(d1, "osloader_resigned.bin"))

    #copy the resigned osloader.bin
    fastboot_fn = os.path.join(d1, "osloader_resigned.bin")
    shutil.copy2(fastboot_fn, out_f)

    #cleanup the temporary directories
    shutil.rmtree(d1)


def process_iasimage(in_f, out_f):
    """
      resign the iasimage with new verity key
    """
    #get the unsigned iasimage binary
    #the method is to get the payload offset plus
    #palyload length plus the crc checksum
    s = struct.Struct('I I I I I I I')
    with open(in_f, 'rb') as fh:
        u = s.unpack(fh.read(struct.calcsize(s.format)))
        data_len = u[3]
        data_off = u[4]
        unsigned_len = data_off + data_len + crc_len
        fh.seek(0,0)
        data = fh.read(unsigned_len)

    tf = tempfile.NamedTemporaryFile()
    tf.write(data)
    tf.flush()

    #resign the fastboot with new verity key
    cmd = ["ias_image_signer"]
    cmd.append(tf.name)
    cmd.extend([OPTIONS.oem_key+".pk8", OPTIONS.oem_key+".x509.pem"])
    cmd.append(out_f)
    p = common.Run(cmd)
    p.wait()
    tf.close()

def main(argv):
    def option_handler(o, a):
        if o in ("-I", "--ifwi-directory"):
            OPTIONS.ifwi_directory = a
        elif o in ("-K", "--oem-key"):
            OPTIONS.oem_key = a
            OPTIONS.all_keys.add(a)
        elif o in ("-V", "--variant"):
            OPTIONS.variant = a
        else:
            return False
        return True

    args = common.ParseOptions(argv, __doc__,
            extra_opts = "I:K:V:",
            extra_long_opts = ["ifwi-directory=", "oem-key=", "variant="],
            extra_option_handler = option_handler)

    if len(args) != 2:
        common.Usage(__doc__)
        sys.exit(1)

    output_fastboot_fn = args[1]

    print "Extracting the provdata.zip"
    prov_file = "provdata_"+OPTIONS.variant+".zip"
    unpack_dir, input_zip = common.UnzipTemp(args[0])
    input_provzip = zipfile.ZipFile(os.path.join(unpack_dir,
                "RADIO", prov_file), "r")

    print "Parsing build.prop for target_product"
    d = {}
    try:
        with open(os.path.join(unpack_dir, "SYSTEM", "build.prop")) as f:
            d = common.LoadDictionaryFromLines(f.read().split("\n"))
    except IOError, e:
       if e.errno == errno.ENOENT:
          raise KeyError(f)
    OPTIONS.target_product = d["ro.product.name"]

    print "Processing private keys"
    OPTIONS.info_dict = common.LoadInfoDict(input_zip)
    passwords = common.GetKeyPasswords(OPTIONS.all_keys)

    #process the provdata.zip to generate resigned one
    process_provzip(input_provzip, output_fastboot_fn)

    common.ZipClose(input_zip)
    print "Extract done."

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except common.ExternalError, e:
        print
        print "   ERROR: %s" % (e,)
        print
        sys.exit(1)
    finally:
        common.Cleanup()
