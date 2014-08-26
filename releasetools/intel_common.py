
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
import shutil

sys.path.append("build/tools/releasetools")
import common


def WriteFileToDest(img, dest):
    """Write common.File to destination"""
    fid = open(dest, 'w')
    fid.write(img.data)
    fid.flush()
    fid.close()


def GetBootloaderImageFromTFP(unpack_dir, autosize=False, extra_files=None):
    if extra_files == None:
        extra_files = []

    bootloader = tempfile.NamedTemporaryFile(delete=False)
    filename = bootloader.name
    bootloader.close()

    fastboot = GetFastbootImage(unpack_dir)
    fastboot_file = fastboot.WriteToTemp()
    extra_files.append((fastboot_file.name,"fastboot.img"))
    if not autosize:
        size = int(open(os.path.join(unpack_dir, "RADIO", "bootloader-size.txt")).read().strip())
    else:
        size = 0
    MakeVFATFilesystem(os.path.join(unpack_dir, "RADIO", "bootloader.zip"),
            filename, size=size, extra_files=extra_files)
    bootloader = open(filename)
    data = bootloader.read()
    bootloader.close()
    fastboot_file.close()
    os.unlink(filename)
    return data


def MakeVFATFilesystem(root_zip, filename, title="ANDROIDIA", size=0, extra_size=0,
        extra_files=[]):
    """Create a VFAT filesystem image with all the files in the provided
    root zipfile. The size of the filesystem, if not provided by the
    caller, will be 101% the size of the containing files"""

    root, root_zip = common.UnzipTemp(root_zip)
    for fn_src, fn_dest in extra_files:
        fn_dest = os.path.join(root, fn_dest)
        if not os.path.exists(os.path.dirname(fn_dest)):
            os.makedirs(os.path.dirname(fn_dest))
        shutil.copy(fn_src, fn_dest)

    if size == 0:
        for dpath, dnames, fnames in os.walk(root):
            for f in fnames:
                print f
                size += os.path.getsize(os.path.join(dpath, f))

        # Add 1% extra space, minimum 32K
        extra = size / 100
        if extra < (32 * 1024):
            extra = 32 * 1024
        size += extra

    size += extra_size

    # Round the size of the disk up to 32K so that total sectors is
    # a multiple of sectors per track (mtools complains otherwise)
    mod = size % (32 * 1024)
    if mod != 0:
        size = size + (32 * 1024) - mod

    # mtools freaks out otherwise
    if os.path.exists(filename):
        os.unlink(filename)

    add_dir_to_path("/sbin")
    cmd = ["mkdosfs", "-n", title, "-C", filename, str(size / 1024)]
    try:
        p = common.Run(cmd)
    except Exception as exc:
        print "Error: Unable to execute command: {}".format(' '.join(cmd))
        raise exc
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
        return common.File.FromLocalFile("fastboot.img", prebuilt_path)

    print "building Fastboot image from target_files..."
    ramdisk_img = tempfile.NamedTemporaryFile()
    img = tempfile.NamedTemporaryFile()

    ramdisk_tmp, ramdisk_zip = common.UnzipTemp(
        os.path.join(unpack_dir, "RADIO", "ufb-ramdisk.zip"))

    cmd1 = ["mkbootfs", ramdisk_tmp]
    try:
        p1 = common.Run(cmd1, stdout=subprocess.PIPE)
    except Exception as exc:
        print "Error: Unable to execute command: {}".format(' '.join(cmd))
        shutil.rmtree(ramdisk_tmp)
        raise exc

    cmd2 = ["minigzip"]
    try:
        p2 = common.Run(
            cmd2, stdin=p1.stdout, stdout=ramdisk_img.file.fileno())
    except Exception as exc:
        print "Error: Unable to execute command: {}".format(' '.join(cmd))
        shutil.rmtree(ramdisk_tmp)
        raise exc

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

    try:
        p = common.Run(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    except Exception as exc:
        print "Error: Unable to execute command: {}".format(' '.join(cmd))
        raise exc
    p.communicate()
    assert p.returncode == 0, "mkbootimg of fastboot image failed"

    # Sign the image using BOOT_SIGNER env variable, or "boot_signer" command
    signing_key = info_dict.get("verity_key")
    if info_dict.get("verity") == "true" and signing_key:
            boot_signer = os.getenv('BOOT_SIGNER') or "boot_signer"
            cmd = [boot_signer, "/boot", img.name, signing_key, img.name];
            try:
                p = common.Run(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            except Exception as exc:
                    print "Error: Unable to execute command: {}".format(' '.join(cmd))
                    raise exc
            p.communicate()
            assert p.returncode == 0, "boot signing of fastboot image failed"

    img.seek(os.SEEK_SET, 0)
    data = img.read()

    ramdisk_img.close()
    img.close()

    return common.File("fastboot.img", data)


def PutFatFile(fat_img, in_path, out_path):
    cmd = ["mcopy", "-s", "-Q", "-i", fat_img, in_path,
           "::" + out_path]
    try:
        p = common.Run(cmd)
    except Exception as exc:
        print "Error: Unable to execute command: {}".format(' '.join(cmd))
        raise exc
    p.wait()
    assert p.returncode == 0, "couldn't insert %s into FAT image" % (in_path,)


def add_dir_to_path(dir_name, end=True):
    """
    I add a directory to the PATH environment variable, if not already in the
    path.  By default it gets added to the end of the PATH
    """
    dir_name = os.path.abspath(dir_name)
    path_env_var = os.environ.get('PATH', "")
    for path_dir in path_env_var.split(os.pathsep):
        path_dir = os.path.abspath(path_dir)
        if dir_name == path_dir:
            return
    if end:
        path_env_var += ":" + dir_name
    else:
        path_env_var = dir_name + ":" + path_env_var
    os.environ['PATH'] = path_env_var

