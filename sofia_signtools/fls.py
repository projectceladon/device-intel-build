# Copyright 2015 Intel Corporations
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
Library functions for manipulating IMC FLS files.

There is just enough functionality supported to support unpacking an FLS
file, signing the internal components and re-packing to an FLS file.

Limitations:
- Only properly supports FLS files with a single 'download_file'
- The download file may only include a single memory region
- SecPacks can only have a single populated LoadMap entry corresponding
  to the download_file
"""
import ast
import collections
import json
import os
import shutil
import struct
import subprocess
import tempfile
import time
import weakref
import Crypto.Hash.hashalgo

FLS_TOOL = os.getenv('FLS_TOOL', 'FlsTool')

def new(fls_path, bswap_secpack_hash, verbose = False, preserve_tmp = False):
    return _FLS(fls_path, bswap_secpack_hash, verbose, preserve_tmp)

class _FLS:
    PRESCRIBED_FLS_ORDER = [
        'fls_version',
        'tool_version',
        'created',
        'last_modified',
        'platform',
        'memory_map',
        'partitions',
        'meta_files',
        'boot_files',
        'download_files'
    ]

    def __init__(self, src_path, bswap_secpack_hash, verbose = False, preserve_tmp = False):
        self._src_path = src_path
        self._verbose = verbose
        self._preserve_tmp = preserve_tmp
        self._dirty = False
        self._bswap_secpack_hash = bswap_secpack_hash
        self._secpack = None
        self._psi = None
        self._tmp_dir = tempfile.mkdtemp()
        self._unpack()

    def __del__(self):
        if not self._preserve_tmp:
            shutil.rmtree(self._tmp_dir)
        else:
            print("Leaving temp dir {} behind".format(self._tmp_dir))

    def __run_and_wait(self, args, **kwargs):
        if self._verbose:
            print("  running: ", " ".join(args))
        subprocess.check_call(args, **kwargs)

    def _unpack(self):
        cmd = [FLS_TOOL,
               "-x", self._src_path,
               "-o", self._tmp_dir]
        self.__run_and_wait(cmd)
        self._read_meta()

    def pack_fls(self, dest_path):
        self.save()

        # Run FlsTool with a cwd that is the immediate parent of the temp
        # unpacked directory, because the -p option only handles cases where
        # the source directory name is the form "dirname/". The trailing "/"
        # is important or FlsTool will not properly identify the internal
        # boot files.

        cmd = [FLS_TOOL,
               "-p", os.path.join(self._tmp_dir, ''),
               "-o", dest_path,
               "--to-fls2", "--replace"]
        self.__run_and_wait(cmd)

    def _read_meta(self):
        with open(os.path.join(self._tmp_dir, "meta.json"), "rb") as meta:
            content = meta.read()
            # the "JSON" output from FlsTool contains extra commas at the
            # end of object and array lists, so it's not actual JSON, but
            # it's a valid Python object. Use second (commented) version as
            # preferred implementation if FlsTool is fixed
            self._meta = ast.literal_eval(content)['intel_fls']
            #self._meta = json.load(meta)['intel_fls']

    def set_dirty(self):
        self._dirty = True

    def save(self):
        if self._secpack is not None:
            self._secpack.save()
        if self._psi is not None:
            self._psi.save()
        if self._dirty:
            with open(os.path.join(self._tmp_dir, "meta.json"), "w") as meta:
                # Use a specialized JSON dump loop to ensure the meta.json
                # has top level attributes in the order FlsTool expects.
                # FlsTool does not properly treat JSON objects as unordered
                # dictionaries of values.
                meta.write('{\n  "intel_fls": {\n')
                for key in _FLS.PRESCRIBED_FLS_ORDER:
                    if key in self._meta:
                        meta.write('    "{}": '.format(key))
                        json.dump(self._meta[key], meta, indent = 2, sort_keys = True)
                        meta.write(',\n')
                meta.write('  }\n}')
                # Use this version of deserialization if FlsTool is fixed
                #wrapper = {}
                #wrapper['intel_fls'] = self._meta
                #json.dump(wrapper, meta, indent = 2)

    def secpack(self):
        if self._secpack:
            return self._secpack
        else:
            secpack_fname = os.path.join(self._tmp_dir, self._meta['download_files'][0]['sec_pack'])
            self._secpack = _SECPACK(self, secpack_fname, self._bswap_secpack_hash)
            return self._secpack

    def psi(self, signed_len):
        if self._psi:
            return self._psi
        else:
            if self._meta['download_files'][0]['orig_file_type'] == "PSI":
                psi_region = self._meta['download_files'][0]['region'][0]
                self._psi = _PSI(self, self.secpack(), psi_region, signed_len)
            else:
                raise Exception("FLS is not a PSI")
            return self._psi

class _SECPACK:
    MIN_SECPACK_LEN = 2048
    SECPACK_PACK_FMT = "".join((
        "<",     # integer fields are little-endian
        "256s",  # 0 Signature0
        "256s",  # 1 Signature1
        "I",     # 2 Type
        "135s",  # 3 DataBlock
        "?",     # 4 UseAlternatePartition
        "I",     # 5 PartitionId
        "I",     # 6 CompressionAlgorithm
        "32s",   # 7 UncompressedLength
        "32s",   # 8 FileHashSha256
        "I",     # 9 BootCoreVersion
        "I",     # 10 EblVersion
        "I",     # 11 Timestamp
        "24s",   # 12 Spare
        "20s",   # 13 FileHashSha1
        "I",     # 14 PartitionMarker
        "1008s", # 15 PartitionEntries
        "12s",   # 16 PartitionReserved
        "112s",  # 17 LoadAddrToPartition
        "I",     # 18 LoadMagic
        "I",     # 19 Loadmap0.StartAddr
        "I",     # 20 Loadmap0.TotalLength
        "I",     # 21 Loadmap0.UsedLength
        "I",     # 22 Loadmap0.ImageFlags
        "112s"   # 23 Loadmap1-7
    ))

    def __init__(self, parent, path, bswap_hash):
        self._parent = weakref.ref(parent)
        self._dirty = False
        self._bswap_hash = bswap_hash

        self._path = path
        with open(self._path, "rb") as secpack:
            self._content = secpack.read()
        self._parts = list(struct.unpack(_SECPACK.SECPACK_PACK_FMT, self._content))

    def __del__(self):
        if self._dirty:
            print("** Warning: dirty _SECPACK deleted without save")

    def __repack(self):
        self._content = struct.pack(_SECPACK.SECPACK_PACK_FMT, *tuple(self._parts))

    def tbs_data(self):
        return self._content[512::]

    def inject_signature(self, sig_data, dev_sig = False):
        if dev_sig:
            sig0 = chr(0) * 256
            sig1 = sig_data
        else:
            sig0 = sig_data
            sig1 = chr(0) * 256

        self._parts[0] = sig0
        self._parts[1] = sig1

        self.__repack()
        self.set_dirty()

    def update_payload_data(self, hash_obj, used_length):
        if self._bswap_hash:
            the_hash = GoofyHash(hash_obj)
        else:
            the_hash = hash_obj
        if isinstance(hash_obj, Crypto.Hash.SHA256.SHA256Hash):
            self._parts[8] = the_hash.digest()
            self._parts[13] = chr(0) * 20
        else:
            self._parts[8] = chr(0) * 32
            self._parts[13] = the_hash.digest()

        self._parts[21] = used_length

        self.__repack()
        self.set_dirty()

    def set_timestamp(self):
        self._parts[11] = int(time.time())

        self.__repack()
        self.set_dirty()

    def set_dirty(self):
        self._dirty = True

    def save(self):
        if self._dirty:
            with open(self._path, "wb") as secpack:
                secpack.write(self._content)
            self._parent()._meta['download_files'][0]['sec_pack_hash']['xor16'] = "0x%04X" % (self.xor16())
            self._dirty = False

    def xor16(self):
        return xor16(self._content)


class _PSI:
    PSI_SIG_SIZE = 0x100

    def __init__(self, parent, secpack, region_info, signed_len):
        self._parent = weakref.ref(parent)
        self._secpack = secpack
        self._dirty = False

        self._region_info = region_info
        self._path = os.path.join(self._parent()._tmp_dir, self._region_info['name'])
        with open(self._path, "rb") as psi:
            self._content = psi.read()

        self._signed_len = signed_len
        if signed_len > int(self._region_info['total_length'], 0):
            raise Exception("signed length cannot be larger than section size")

        # Return an error in cases where the content to be signed is either
        # longer than the desired signed length or the length is long
        # enough to end in the middle of the signature block
        if (len(self._content) > signed_len or
            ((len(self._content) > (signed_len - _PSI.PSI_SIG_SIZE)) and
             (len(self._content) < signed_len))):
            raise Exception("input data cannot be reliably signed")


    def tbs_data(self):
        if len(self._content) < (self._signed_len - _PSI.PSI_SIG_SIZE):
            # Add enough bytes for padding and signature block
            # Don't mark the data dirty yet since we're only speculatively
            # adding padding.
            pad_len = self._signed_len - len(self._content)
            pad_str = chr(0xff) * pad_len
            self._content += pad_str

        return self._content[0:self._signed_len - _PSI.PSI_SIG_SIZE]

    def inject_signature(self, sig_data):
        if len(sig_data) != _PSI.PSI_SIG_SIZE:
            raise Exception("signature should be %d bytes long" % (_PSI.PSI_SIG_SIZE))

        self._content = self._content[0:self._signed_len - _PSI.PSI_SIG_SIZE] + sig_data
        self._region_info['used_length'] = "0x%08X" % (self._signed_len)
        self._region_info['hash']['xor16'] = "0x%04X" % (self.xor16())

        self._secpack.update_payload_data(Crypto.Hash.SHA256.new(self._content), self._signed_len)
        self.set_dirty()

    def set_dirty(self):
        self._dirty = True
        self._parent().set_dirty()

    def save(self):
        if self._dirty:
            with open(self._path, "wb") as psi:
                psi.write(self._content)
            self._dirty = False

    def xor16(self):
        return xor16(self._content)

class GoofyHash(Crypto.Hash.hashalgo.HashAlgo):
    """Wraps a pycrypto hash algorithm instance to return a "goofy" hash
    value, where each 32 bit word in the output has least significant byte
    first.
    """

    def __init__(self, inner):
        self.__inner = inner
        self.oid = inner.oid

    def update(self, data):
        self.__inner.update(data)

    def digest(self):
        orig = self.__inner.digest()

        num_words = len(orig) / 4
        unpack_fmt = "<" + ("I" * num_words)
        pack_fmt = ">" + ("I" * num_words)

        words = struct.unpack(unpack_fmt, orig)
        #print words
        return struct.pack(pack_fmt, *words)

    def hexdigest(self):
        orig = self.digest()
        return "".join("{:02x}".format(ord(c)) for c in orig)

    def copy(self):
        return GoofyHash(self.__inner.copy())

    def new(self, data=None):
        return GoofyHash(self.__inner.new(data))

def xor16(content):
    data = [0, 0]
    for i in range(0, len(content)):
        data[i % 2] ^= ord(content[i])
    return (data[1] << 8) + data[0]
