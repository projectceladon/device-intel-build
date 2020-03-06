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
Extract fastboot binary from TFP and resign fastboot binary in ABL based platform
keys.
Usage: extract_fastboot.py <options> <input_target_files_zip> <output_file>
  -K  (--oem-key) <path to new keypair>
      Replace the OEM key inside kernelflinger with the replacement copy.
      The OEM keystore must be signed with this key.
      Expects a key pair assuming private key ends in .pk8 and public key
      with .x509.pem

  -A  (--avb-key) <path>
      Replace the Android Verified Boot key with the key in path

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
    print("Python 2.4 or newer is required.", file=sys.stderr)
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
OPTIONS.avb_key = None
OPTIONS.target_product = None

crc_len = 4
ias_image_type_str = "0x40300"
section_entry_sz = 0x28
fastboot_component_num = 4

def get_section(data, name):
    section_table_offset = struct.unpack_from("<I", data, 0x20)[0]
    num_sections, str_table_idx = struct.unpack_from("<HH", data, 0x30)
    str_table_offset = section_table_offset + (str_table_idx * section_entry_sz)
    _, _, _, _, str_section_offset, str_section_size, _, _, _, _ = struct.unpack_from("<10I", data, str_table_offset)

    for i in range(num_sections):
        section_offset = section_table_offset + (i * section_entry_sz)
        section_table_data = struct.unpack_from("<10I", data, section_offset)

        section_name_idx, _, _, _, section_offset, section_size,  _, _, _, _ = section_table_data
        section_name = data[str_section_offset + section_name_idx:str_section_offset + section_name_idx + len(name)]
        if section_name != name:
            continue
        print("Found", section_name, "at offset", hex(section_offset))
        return (section_offset, section_size)

    raise common.ExternalError("Section not found")

def replace_raw_keys(data, raw_key, password):
    (oemkeys_offset, oemkeys_size) = get_section(data, ".oemkeys")

    oem_key_file = open(raw_key, "rb")
    oem_key_data = zero_pad(oem_key_file.read(), oemkeys_size)
    oem_key_file.close()

    data = (data[:oemkeys_offset] + oem_key_data +
            data[oemkeys_offset + oemkeys_size:])
    return data

def zero_pad(data, size):
    if len(data) > size:
        raise common.ExternalError("Binary is already larger than pad size")

    return data + (b'\x00' * (size - len(data)))

def process_fastboot(in_f, out_f):
    """
       get the abl binary from the in_f
       replace the .oemkeys section
       then combine back to a signed ias image
       with the new key
    """
    s = struct.Struct('11I')
    fh = open(in_f, "rb")
    u = s.unpack(fh.read(struct.calcsize(s.format)))
    data_len = u[3]
    data_off = u[4]

    fp = os.path.dirname(os.path.abspath(in_f))
    fh.seek(data_off, 0)
    for i in range(fastboot_component_num):
        comp_len = u[7+i]
        fn = os.path.join(fp, "comp"+str(i))
        fc = open(fn, "wb")
        data = fh.read(comp_len)
        if i == 1:
            print("Replacing .oemkeys inside abl binary")
            password = None
            data = replace_raw_keys(data, OPTIONS.avb_key, password)
        fc.write(data)
        fc.close()

    #combine the individual component files back into the ias image
    unsigned_fastboot_fn = os.path.join(fp, "fastboot_unsigned.bin")
    cmd = ["ias_image_app"]
    cmd.extend(["-i", ias_image_type_str])
    cmd.extend(["-o", unsigned_fastboot_fn])
    for i in range(fastboot_component_num):
        fn = os.path.join(fp, "comp"+str(i))
        cmd.append(fn)
    p = common.Run(cmd)
    p.wait()
    fh.close()

    process_iasimage(unsigned_fastboot_fn, out_f)

def process_provzip(input_provzip, output_fn):
    path = "fastboot"
    dn = tempfile.mkdtemp()
    in_fname = input_provzip.extract(path, dn)
    if OPTIONS.avb_key == None:
        process_iasimage(in_fname, output_fn)
    else:
        process_fastboot(in_fname, output_fn)
    shutil.rmtree(dn)

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
        elif o in ("-A", "--avb-key"):
            OPTIONS.avb_key = a
            OPTIONS.all_keys.add(a)
        elif o in ("-K", "--oem-key"):
            OPTIONS.oem_key = a
            OPTIONS.all_keys.add(a)
        elif o in ("-V", "--variant"):
            OPTIONS.variant = a
        else:
            return False
        return True

    args = common.ParseOptions(argv, __doc__,
            extra_opts = "I:A:K:V:",
            extra_long_opts = ["ifwi-directory=", "avb-key=", "oem-key=", "variant="],
            extra_option_handler = option_handler)

    if len(args) != 2:
        common.Usage(__doc__)
        sys.exit(1)

    output_fastboot_fn = args[1]

    print("Extracting the provdata.zip")
    prov_file = "provdata_"+OPTIONS.variant+".zip"
    unpack_dir = common.UnzipTemp(args[0])
    input_zip = zipfile.ZipFile(args[0], "r")
    input_provzip = zipfile.ZipFile(os.path.join(unpack_dir,
                "RADIO", prov_file), "r")

    print("Parsing build.prop for target_product")
    d = {}
    try:
        with open(os.path.join(unpack_dir, "SYSTEM", "build.prop")) as f:
            d = common.LoadDictionaryFromLines(f.read().split("\n"))
    except IOError as e:
       if e.errno == errno.ENOENT:
          raise KeyError(f)
    OPTIONS.target_product = d["ro.product.name"]

    print("Processing private keys")
    OPTIONS.info_dict = common.LoadInfoDict(input_zip)
    passwords = common.GetKeyPasswords(OPTIONS.all_keys)

    #process the provdata.zip to generate resigned one
    process_provzip(input_provzip, output_fastboot_fn)

    common.ZipClose(input_zip)
    print("Extract done.")

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except common.ExternalError as e:
        print()
        print("   ERROR: %s" % (e,))
        print()
        sys.exit(1)
    finally:
        common.Cleanup()
