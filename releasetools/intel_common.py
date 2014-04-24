
#
# Copyright (C) 2014 The Android Open Source Project
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


import tempfile
import os
import sys
import subprocess
import shlex

sys.path.append("build/tools/releasetools")
import common

def WriteFileToDest(img, dest):
    """Write common.File to destination"""
    fid = open(dest, 'w')
    fid.write(img.data)
    fid.flush()
    fid.close()

def MakeVFATFilesystem(root_zip, filename, title="ANDROIDIA", size=0):
    """Create a VFAT filesystem image with all the files in the provided
    root zipfile. The size of the filesystem, if not provided by the
    caller, will be 101% the size of the containing files"""

    root, root_zip = common.UnzipTemp(root_zip)
    if size == 0:
        for dpath, dnames, fnames in os.walk(root):
            for f in fnames:
                size += os.path.getsize(os.path.join(dpath, f))

        # Add 1% extra space, minimum 32K
        extra = size / 100
        if extra < (32 * 1024):
            extra = 32 * 1024
        size += extra

    # Round the size of the disk up to 32K so that total sectors is
    # a multiple of sectors per track (mtools complains otherwise)
    mod = size % (32 * 1024)
    if mod != 0:
        size = size + (32 * 1024) - mod

    # mtools freaks out otherwise
    if os.path.exists(filename):
        os.unlink(filename)

    cmd = ["mkdosfs", "-n", title, "-C", filename, str(size / 1024)]
    p = common.Run(cmd)
    p.wait()
    assert p.returncode == 0, "mkdosfs failed"
    for f in os.listdir(root):
        in_p = os.path.join(root, f)
        out_p = os.path.relpath(in_p, root)
        PutFatFile(filename, in_p, out_p)


def GetFastbootImage(unpack_dir, info_dict=None):
    """Return a File object 'fastboot.img' with the Fastboot boot image.
    It will either be fetched from BOOTABLE_IMAGES/fastboot.img or built
    using RADIO/ufb_ramdisk.zip, RADIO/ufb_cmdline, and BOOT/kernel"""

    if info_dict is None:
        info_dict = common.OPTIONS.info_dict

    prebuilt_path = os.path.join(unpack_dir, "BOOTABLE_IMAGES", "fastboot.img")
    if (os.path.exists(prebuilt_path)):
        print "using prebuilt fastboot.img"
        return File.FromLocalFile(name, prebuilt_path)

    print "building Fastboot image from target_files..."
    ramdisk_img = tempfile.NamedTemporaryFile()
    img = tempfile.NamedTemporaryFile()

    ramdisk_tmp, ramdisk_zip = common.UnzipTemp(os.path.join(unpack_dir,
            "RADIO", "ufb-ramdisk.zip"))

    cmd = ["mkbootfs", ramdisk_tmp]
    p1 = common.Run(cmd, stdout=subprocess.PIPE)
    p2 = common.Run(["minigzip"], stdin=p1.stdout, stdout=ramdisk_img.file.fileno())

    p2.wait()
    p1.wait()
    assert p1.returncode == 0, "mkbootfs of fastboot ramdisk failed"
    assert p2.returncode == 0, "minigzip of fastboot ramdisk failed"

    # use MKBOOTIMG from environ, or "mkbootimg" if empty or not set
    mkbootimg = os.getenv('MKBOOTIMG') or "mkbootimg"

    cmd = [mkbootimg, "--kernel", os.path.join(unpack_dir, "BOOT", "kernel")]
    fn = os.path.join(unpack_dir, "RADIO", "ufb-cmdline")
    if os.access(fn, os.F_OK):
        cmd.append("--cmdline")
        cmd.append(open(fn).read().rstrip("\n"))

    # Add 2nd-stage loader, if it exists
    fn = os.path.join(unpack_dir, "RADIO", "ufb-second")
    if os.access(fn, os.F_OK):
        cmd.append("--second")
        cmd.append(fn)

    args = info_dict.get("mkbootimg_args", None)
    if args and args.strip():
        cmd.extend(shlex.split(args))

    cmd.extend(["--ramdisk", ramdisk_img.name,
                "--output", img.name])

    p = common.Run(cmd, stdout=subprocess.PIPE)
    p.communicate()
    assert p.returncode == 0, "mkbootimg of fastboot image failed"

    img.seek(os.SEEK_SET, 0)
    data = img.read()

    ramdisk_img.close()
    img.close()

    return common.File("fastboot.img", data)

def PutFatFile(fat_img, in_path, out_path):
    cmd = ["mcopy", "-s", "-Q", "-i", fat_img, in_path,
            "::"+out_path]
    p = common.Run(cmd)
    p.wait()
    assert p.returncode == 0, "couldn't insert %s into FAT image" % (in_path,)

