
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


def GetFastbootImage(unpack_dir, info_dict=None, password=None):
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
        raise exc

    cmd2 = ["minigzip"]
    try:
        p2 = common.Run(
            cmd2, stdin=p1.stdout, stdout=ramdisk_img.file.fileno())
    except Exception as exc:
        print "Error: Unable to execute command: {}".format(' '.join(cmd))
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
    if password is not None:
        password += "\n"
    p.communicate(password)
    assert p.returncode == 0, "mkbootimg of fastboot image failed"

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

# Variant of the version inside common.py; can communicate a password
# to mkbootimg. Key path is stored in mkbootimg_args; modify that
# before calling this
def BuildBootableImage(sourcedir, fs_config_file, info_dict=None, password=None):
    """Take a kernel, cmdline, and ramdisk directory from the input (in
    'sourcedir'), and turn them into a boot image.  Return the image
    data, or None if sourcedir does not appear to contains files for
    building the requested image."""

    if (not os.access(os.path.join(sourcedir, "RAMDISK"), os.F_OK) or
            not os.access(os.path.join(sourcedir, "kernel"), os.F_OK)):
        return None

    if info_dict is None:
        info_dict = common.OPTIONS.info_dict

    ramdisk_img = tempfile.NamedTemporaryFile()
    img = tempfile.NamedTemporaryFile()

    if os.access(fs_config_file, os.F_OK):
        cmd = ["mkbootfs", "-f", fs_config_file, os.path.join(sourcedir, "RAMDISK")]
    else:
        cmd = ["mkbootfs", os.path.join(sourcedir, "RAMDISK")]
    p1 = common.Run(cmd, stdout=subprocess.PIPE)
    p2 = common.Run(["minigzip"],
           stdin=p1.stdout, stdout=ramdisk_img.file.fileno())

    p2.wait()
    p1.wait()
    assert p1.returncode == 0, "mkbootfs of %s ramdisk failed" % (targetname,)
    assert p2.returncode == 0, "minigzip of %s ramdisk failed" % (targetname,)

    # use MKBOOTIMG from environ, or "mkbootimg" if empty or not set
    mkbootimg = os.getenv('MKBOOTIMG') or "mkbootimg"

    cmd = [mkbootimg, "--kernel", os.path.join(sourcedir, "kernel")]

    fn = os.path.join(sourcedir, "cmdline")
    if os.access(fn, os.F_OK):
        cmd.append("--cmdline")
        cmd.append(open(fn).read().rstrip("\n"))

    fn = os.path.join(sourcedir, "base")
    if os.access(fn, os.F_OK):
        cmd.append("--base")
        cmd.append(open(fn).read().rstrip("\n"))

    fn = os.path.join(sourcedir, "pagesize")
    if os.access(fn, os.F_OK):
        cmd.append("--pagesize")
        cmd.append(open(fn).read().rstrip("\n"))

    args = info_dict.get("mkbootimg_args", None)
    if args and args.strip():
        cmd.extend(shlex.split(args))

    cmd.extend(["--ramdisk", ramdisk_img.name,
                "--output", img.name])

    p = common.Run(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    if password is not None:
        password += "\n"
    p.communicate(password)
    assert p.returncode == 0, "mkbootimg of %s image failed" % (
        os.path.basename(sourcedir),)

    img.seek(os.SEEK_SET, 0)
    data = img.read()

    ramdisk_img.close()
    img.close()

    return data

# Variant of the version inside common.py; can communicate a password
# to mkbootimg
def GetBootableImage(name, prebuilt_name, unpack_dir, tree_subdir,
                     info_dict=None, password=None):
    """Return a File object (with name 'name') with the desired bootable
    image.  Look for it in 'unpack_dir'/BOOTABLE_IMAGES under the name
    'prebuilt_name', otherwise construct it from the source files in
    'unpack_dir'/'tree_subdir'."""

    prebuilt_path = os.path.join(unpack_dir, "BOOTABLE_IMAGES", prebuilt_name)
    if os.path.exists(prebuilt_path):
        print "using prebuilt %s..." % (prebuilt_name,)
        return common.File.FromLocalFile(name, prebuilt_path)
    else:
        print "building image from target_files %s..." % (tree_subdir,)
        fs_config = "META/" + tree_subdir.lower() + "_filesystem_config.txt"
    return common.File(name, BuildBootableImage(os.path.join(unpack_dir, tree_subdir),
                                         os.path.join(unpack_dir, fs_config),
                                         info_dict, password))

