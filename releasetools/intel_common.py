
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
import os, errno
import sys
import subprocess
import shlex
import shutil
import imp
import time
import collections
import fnmatch
import time
import json
import zipfile
import re
import random
from cStringIO import StringIO

sys.path.append("build/tools/releasetools")
import common


def load_device_mapping(path):
    try:
        mod = imp.load_module("device_mapping", open(path, "U"), path,
                              (".py", "U", imp.PY_SOURCE))
    except ImportError:
        print "Device mapping not found"
        return None

    return mod.dmap


def load_device_mapping_from_tfp(tfp_path):
    return load_device_mapping(os.path.join(tfp_path, "RADIO",
                                            "device_mapping.py"))


def der_pub_from_pem_cert(cert_path):
    tf = tempfile.NamedTemporaryFile(prefix="der_pub_from_pem_cert")

    cmd1 = ["openssl", "x509",
            "-in", cert_path,
            "-noout", "-pubkey"]
    cmd2 = ["openssl", "rsa",
            "-inform", "PEM",
            "-pubin",
            "-outform", "DER",
            "-out", tf.name]
    p1 = common.Run(cmd1, stdout=subprocess.PIPE)
    p2 = common.Run(cmd2, stdin=p1.stdout)
    p2.communicate()
    p1.wait()
    assert p1.returncode == 0, "extracting verity public key failed"
    assert p2.returncode == 0, "verity public key conversion failed"

    tf.seek(os.SEEK_SET, 0)
    return tf


def pem_cert_to_der_cert(pem_cert_path):
    tf = tempfile.NamedTemporaryFile(prefix="pem_cert_to_der_cert")

    cmd = ["openssl", "x509", "-inform", "PEM", "-outform", "DER",
        "-in", pem_cert_path, "-out", tf.name]
    p = common.Run(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.communicate()
    assert p.returncode == 0, "openssl cert conversion failed"
    tf.seek(os.SEEK_SET, 0)
    return tf


def pk8_to_pem(der_key_path, password=None, none_on_fail_convert=False):
    # If the key is already available in converted form, then use that
    # file. This is important for .pk8 files that actually contain references
    # to ECSS keys, because they are not fully parseable by openssl.
    (der_key_path_root,der_key_path_ext) = os.path.splitext(der_key_path)
    der_key_path_pem = der_key_path_root + ".pem"
    if os.path.exists(der_key_path_pem):
        return open(der_key_path_pem)

    # Defaults to 0600 permissions which is defintitely what we want!
    tf = tempfile.NamedTemporaryFile(prefix="pk8_to_pem")

    cmd = ["openssl", "pkcs8"];
    if password:
        cmd.extend(["-passin", "stdin"])
    else:
        cmd.append("-nocrypt")

    cmd.extend(["-inform", "DER", "-outform", "PEM",
        "-in", der_key_path, "-out", tf.name])
    p = common.Run(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    if password is not None:
        password += "\n"
    p.communicate(password)
    if none_on_fail_convert:
        if p.returncode != 0:
            tf.close()
            return None
    else:
        assert p.returncode == 0, "openssl key conversion failed"
    tf.seek(os.SEEK_SET, 0)
    return tf


def WriteFileToDest(img, dest):
    """Write common.File to destination"""
    fid = open(dest, 'w')
    fid.write(img.data)
    fid.flush()
    fid.close()


def patch_or_verbatim_exists(filepath, ota_zip):
    patchpath = os.path.join("patch", filepath + ".p")
    return filepath in ota_zip.namelist() or patchpath in ota_zip.namelist()


def AddFWImageFile(input_dir, output_zip, variant=None):
    # AddFWImageFile reads the fwu_image file from provdata in input_dir
    # and writes it into the output_zip.
    # When called by ota_from_target_files for specifc variants an empty
    # fwu_image is written into output_zip.
    fwu_image = readfile_from_provdata(input_dir, "fwu_image.bin", variant)

    if fwu_image is None:
        fwu_image = ""
    common.ZipWriteStr(output_zip, "fwu_image.bin", fwu_image)

def readfile_from_provdata(tmpdir, path, variant=None):
    if variant:
        provdata = "provdata_" + variant + ".zip"
    else:
        provdata = "provdata.zip"
    provdata_name = os.path.join(tmpdir, "RADIO", provdata)
    provdata_dir = os.path.join(tmpdir, "RADIO")

    if provdata in os.listdir(provdata_dir):
        with zipfile.ZipFile(provdata_name) as provdata_zip:
            data = provdata_zip.read(path)
        return data


def ComputeFWUpdatePatches(source_tfp_dir, target_tfp_dir, variant=None,
                             existing_ota_zip=None):
    patch_list = None
    verbatim = None
    output_files = None

    # In case an already "fixed up" ota package is passed - Do nothing
    if existing_ota_zip and patch_or_verbatim_exists("fwu_image.bin", existing_ota_zip):
        return verbatim, patch_list, output_files

    src_fwupdate_data = readfile_from_provdata(source_tfp_dir, "fwu_image.bin", variant)
    if not src_fwupdate_data:
        return verbatim, patch_list, output_files

    tgt_fwupdate_data = readfile_from_provdata(target_tfp_dir, "fwu_image.bin", variant)
    if not tgt_fwupdate_data:
        return verbatim, patch_list, output_files

    src_fwupdate = common.File("fwu_image.bin", src_fwupdate_data)
    tgt_fwupdate = common.File("fwu_image.bin", tgt_fwupdate_data)

    diffs = [common.Difference(tgt_fwupdate, src_fwupdate)]
    common.ComputeDifferences(diffs)

    tf, sf, d = diffs[0].GetPatch()
    verbatim = False
    # If the patch size is almost as big as the actual file
    # the fwu_image will be included in the OTA verbatim.
    if d is None or len(d) > tf.size * 0.95:
        print "Firmware update image will be included verbatim"
        verbatim = True
    else:
        patch_list = (tf,sf)
        output_files = d
    return verbatim, patch_list, output_files


def ComputeBootloaderPatch(source_tfp_dir, target_tfp_dir, variant=None,
                           base_variant=None, existing_ota_zip=None):
    target_data = LoadBootloaderFiles(target_tfp_dir, variant=variant, base_variant=base_variant)
    source_data = LoadBootloaderFiles(source_tfp_dir, variant=variant, base_variant=base_variant)

    diffs = []

    # List of files that will be included in the OTA verbatim because
    # they are either new or the patch is > 95% in size of the original
    # file. If this isn't empty you just need to call edify generator
    # UnpackPackageDir("bootloader", "/bootloader")
    verbatim_targets = []

    # Returned list of common.File objects that need to be added to
    # the OTA archive, for each one call AddToZip()
    output_files = []

    # Returned list of patches to be created.
    # Each element is a tuple of the form (path, target File object,
    # source File object, target file size)
    patch_list = []

    for fn in sorted(target_data.keys()):
        filepath = os.path.join('bootloader', fn)
        if existing_ota_zip and patch_or_verbatim_exists(filepath, existing_ota_zip):
            continue

        tf = target_data[fn]
        sf = source_data.get(fn, None)

        if sf is None:
            verbatim_targets.append(fn)
            output_files.append(tf)
        elif tf.sha1 != sf.sha1:
            diffs.append(common.Difference(tf, sf))

    common.ComputeDifferences(diffs)

    for diff in diffs:
        tf, sf, d = diff.GetPatch()
        if d is None or len(d) > tf.size * 0.95:
            output_files.append(tf)
            verbatim_targets.append(tf.name)
        else:
            output_files.append(common.File("patch/" + tf.name + ".p", d))
            patch_list.append((tf, sf))

    # output list of files that need to be deleted, pass this to
    # edify generator DeleteFiles in InstallEnd
    delete_files = ["/bootloader/"+i for i in sorted(source_data) if i not in target_data]

    return (output_files, delete_files, patch_list, verbatim_targets)


def LoadBootloaderFiles(tfpdir, extra_files=None, variant=None, base_variant=None):
    out = {}
    data = GetBootloaderImageFromTFP(tfpdir, extra_files=extra_files,
                                     variant=variant, base_variant=base_variant)
    image = common.File("bootloader.img", data).WriteToTemp()

    # Extract the contents of the VFAT bootloader image so we
    # can compute diffs on a per-file basis
    esp_root = tempfile.mkdtemp(prefix="bootloader-")
    common.OPTIONS.tempfiles.append(esp_root)
    add_dir_to_path("/sbin")
    subprocess.check_output(["mcopy", "-s", "-i", image.name, "::*", esp_root]);
    image.close();

    for dpath, dname, fnames in os.walk(esp_root):
        for fname in fnames:
            # Capsule update file -- gets consumed and deleted by the firmware
            # at first boot, shouldn't try to patch it
            if (fname == "BIOSUPDATE.fv"):
                continue
            abspath = os.path.join(dpath, fname)
            relpath = os.path.relpath(abspath, esp_root)
            data = open(abspath).read()
            out[relpath] = common.File("bootloader/" + relpath, data)

    return out


def GetBootloaderImageFromTFP(unpack_dir, autosize=False, extra_files=None, variant=None, base_variant=None):
    info_dict = common.OPTIONS.info_dict
    if extra_files == None:
        extra_files = []
    platform_efi, platform_sflte = CheckIfSocEFI(unpack_dir, variant)

    if variant and platform_efi:
        provdata_name = os.path.join(unpack_dir, "RADIO", "provdata_" + variant +".zip")
        if base_variant and (os.path.isfile(provdata_name) == False):
            provdata_name = os.path.join(unpack_dir, "RADIO", "provdata_" + base_variant +".zip")
        provdata, provdata_zip = common.UnzipTemp(provdata_name)
        cap_path = os.path.join(provdata,"capsule.fv")
        if os.path.exists(cap_path):
            extra_files.append((cap_path, "capsules/current.fv"))
            extra_files.append((cap_path, "BIOSUPDATE.fv"))
        else:
            print "No capsule.fv found in provdata_" + variant + ".zip"
        base_bootloader = os.path.join(provdata, "BOOTLOADER")
        if os.path.exists(base_bootloader):
            for root, dirs, files in os.walk(base_bootloader):
                for name in files:
                    fullpath = os.path.join(root, name)
                    relpath = os.path.relpath(fullpath, base_bootloader)
                    print "Adding extra bootloader file", relpath
                    extra_files.append((fullpath, relpath))

    if not platform_efi:
        if variant:
            provdata_name = os.path.join(unpack_dir, "RADIO", "provdata_" + variant + ".zip")
        else:
            provdata_name = os.path.join(unpack_dir, "RADIO", "provdata" + ".zip")
        provdata, provdata_zip = common.UnzipTemp(provdata_name)
        filename = os.path.join(provdata, "bootloader")
    else:
        bootloader = tempfile.NamedTemporaryFile(delete=False)
        filename = bootloader.name
        bootloader.close()

        fastboot = GetFastbootImage(unpack_dir)
        if fastboot:
            fastboot_file = fastboot.WriteToTemp()
            extra_files.append((fastboot_file.name,"fastboot.img"))

        tdos = GetTdosImage(unpack_dir)
        if tdos:
            tdos_file = tdos.WriteToTemp()
            extra_files.append((tdos_file.name,"tdos.img"))

        info_dir = os.path.join(unpack_dir, "RADIO")
        info = GetBootloaderInfo(info_dir, autosize)

        MakeVFATFilesystem(os.path.join(unpack_dir, "RADIO", "bootloader.zip"),
                           filename, size=int(info["size"]),
                           block_size=info["block_size"],
                           extra_files=extra_files)

    bootloader = open(filename)
    data = bootloader.read()
    bootloader.close()
    os.unlink(filename)
    return data

def GetBootloaderInfo(info_dir, autosize):
    info_file = os.path.join(info_dir, "bootloader_image_info.txt")
    if os.path.isfile(info_file):
        info = common.LoadDictionaryFromLines(open(info_file).readlines())
    else:
        # Preserve legacy way to get size to keep OTA generation scripts working
        info = {}
        info_file = os.path.join(info_dir, "bootloader-size.txt")
        info["size"] = int(open(info_file).read().strip())
        info["block_size"] = None

    if autosize:
        info["size"] = 0

    return info

def GetBootloaderImageFromOut(product_out, intermediate_dir, filename, autosize=False, extra_files=None):
    if extra_files == None:
        extra_files = []

    fastboot = os.path.join(product_out, "fastboot.img")
    if os.path.exists(fastboot):
        print "add fastboot.img to bootloader"
        extra_files.append((fastboot, "fastboot.img"))

    tdos = os.path.join(product_out, "tdos.img")
    if os.path.exists(tdos):
        print "add tdos.img to bootloader"
        extra_files.append((tdos, "tdos.img"))

    info_dir = os.path.join(intermediate_dir, "../")
    info = GetBootloaderInfo(info_dir, autosize)

    MakeVFATFilesystem(intermediate_dir, filename, size=int(info["size"]),
                       block_size=info["block_size"],
                       extra_files=extra_files, zipped=False)

def MakeVFATFilesystem(root_zip, filename, title="ANDROIDIA", size=0, block_size=None, extra_size=0,
        extra_files=[], zipped=True):
    """Create a VFAT filesystem image with all the files in the provided
    root zipfile. The size of the filesystem, if not provided by the
    caller, will be 101% the size of the containing files"""

    if zipped:
        root, root_zip = common.UnzipTemp(root_zip)
    else:
        root = root_zip

    for fn_src, fn_dest in extra_files:
        fn_dest = os.path.join(root, fn_dest)
        if not os.path.exists(os.path.dirname(fn_dest)):
            os.makedirs(os.path.dirname(fn_dest))
        shutil.copy(fn_src, fn_dest)

    if size == 0:
        for dpath, dnames, fnames in os.walk(root):
            for f in fnames:
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
    cmd = ["mkdosfs"]
    if block_size:
        cmd.extend(["-S", str(block_size)])
    cmd.extend(["-n", title, "-C", filename, str(size / 1024)])
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


def GetTdosImage(unpack_dir, info_dict=None):
    if info_dict is None:
        info_dict = common.OPTIONS.info_dict

    prebuilt_path = os.path.join(unpack_dir, "RADIO", "tdos.img")
    if (os.path.exists(prebuilt_path)):
        print "using prebuilt tdos.img"
        return common.File.FromLocalFile("tdos.img", prebuilt_path)

    ramdisk_path = os.path.join(unpack_dir, "RADIO", "ramdisk-tdos.img")
    if not os.path.exists(ramdisk_path):
        print "no TDOS ramdisk found"
        return None

    print "building TDOS image from target_files..."
    ramdisk_img = tempfile.NamedTemporaryFile()
    img = tempfile.NamedTemporaryFile()

    # use MKBOOTIMG from environ, or "mkbootimg" if empty or not set
    mkbootimg = os.getenv('MKBOOTIMG') or "mkbootimg"

    cmd = [mkbootimg, "--kernel", os.path.join(unpack_dir, "BOOT", "kernel")]
    fn = os.path.join(unpack_dir, "BOOT", "cmdline")
    if os.access(fn, os.F_OK):
        cmd.append("--cmdline")
        cmd.append(open(fn).read().rstrip("\n"))

    # Add 2nd-stage loader, if it exists
    fn = os.path.join(unpack_dir, "BOOT", "second")
    if os.access(fn, os.F_OK):
        cmd.append("--second")
        cmd.append(fn)

    args = info_dict.get("mkbootimg_args", None)
    if args and args.strip():
        cmd.extend(shlex.split(args))

    cmd.extend(["--ramdisk", ramdisk_path,
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
            cmd = [boot_signer, "/tdos", img.name,
                    signing_key + common.OPTIONS.private_key_suffix,
                    signing_key + common.OPTIONS.public_key_suffix, img.name];
            try:
                p = common.Run(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            except Exception as exc:
                    print "Error: Unable to execute command: {}".format(' '.join(cmd))
                    raise exc
            p.communicate()
            assert p.returncode == 0, "boot signing of tdos image failed"

    img.seek(os.SEEK_SET, 0)
    data = img.read()

    img.close()

    return common.File("tdos.img", data)


def GetFastbootImage(unpack_dir, info_dict=None):
    """Return a File object 'fastboot.img' with the Fastboot boot image.
    It will either be fetched from RADIO/fastboot.img or built
    using RADIO/ufb_ramdisk.zip, RADIO/ufb_cmdline, and BOOT/kernel"""

    if info_dict is None:
        info_dict = common.OPTIONS.info_dict

    prebuilt_path = os.path.join(unpack_dir, "RADIO", "fastboot.img")
    if (os.path.exists(prebuilt_path)):
        print "using prebuilt fastboot.img"
        return common.File.FromLocalFile("fastboot.img", prebuilt_path)

    ramdisk_path = os.path.join(unpack_dir, "RADIO", "ufb-ramdisk.zip")
    if not os.path.exists(ramdisk_path):
        print "no user fastboot image found, assuming efi fastboot"
        return None

    print "building Fastboot image from target_files..."
    ramdisk_img = tempfile.NamedTemporaryFile()
    img = tempfile.NamedTemporaryFile()

    ramdisk_tmp, ramdisk_zip = common.UnzipTemp(ramdisk_path)

    cmd1 = ["mkbootfs", ramdisk_tmp]
    try:
        p1 = common.Run(cmd1, stdout=subprocess.PIPE)
    except Exception as exc:
        print "Error: Unable to execute command: {}".format(' '.join(cmd1))
        shutil.rmtree(ramdisk_tmp)
        raise exc

    cmd2 = ["minigzip"]
    try:
        p2 = common.Run(
            cmd2, stdin=p1.stdout, stdout=ramdisk_img.file.fileno())
    except Exception as exc:
        print "Error: Unable to execute command: {}".format(' '.join(cmd2))
        shutil.rmtree(ramdisk_tmp)
        raise exc

    p1.stdout.close()
    p2.communicate()
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
            cmd = [boot_signer, "/fastboot", img.name,
                    signing_key + common.OPTIONS.private_key_suffix,
                    signing_key + common.OPTIONS.public_key_suffix, img.name];
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


# dictionnary to translate Makefile "target" name to filename
def init_t2f_dict(t2f_list):
    d = {}
    for l in t2f_list.split():
        target, fname = l.split(':')
        d[target] = fname
    return d


def get_tag(target):
    t2tag = { "system": "SYSTEM",
              "userdata": "USERDATA",
              "cache": "CACHE",
              "boot": "BOOT_IMG",
              "recovery": "RECOVERY"}
    return t2tag[target]


def get_psi(dir, t2f):
    if (t2f["PSI_RAM_FLS"] != '') and (t2f["EBL_FLS"] != ''):
        return [os.path.join(dir, os.path.basename(t2f["PSI_RAM_FLS"])),
                os.path.join(dir, os.path.basename(t2f["EBL_FLS"]))]
    return [None, None]


def check_signed_fls(target):
    if target.endswith("_signed.fls"):
        return [True, target[:-11]]
    elif target.endswith(".fls"):
        return [False, target[:-4]]
    raise Exception("Unknown target type")


def run_cmd(cmd):
    try:
        p = common.Run(cmd)
    except Exception as exc:
        print "Error: Unable to execute command: {}".format(' '.join(cmd))
        raise exc
    p.communicate()
    assert p.returncode == 0, "Command failed: {}".format(' '.join(cmd))


def run_fls(flstool, prg, output, tag, infile, psi, eblsec):

    cmd = [flstool, "--prg", prg,
                    "--output", output,
                    "--tag", tag]

    if psi and eblsec:
        cmd.extend(["--psi", psi])
        cmd.extend(["--ebl-sec", eblsec])

    cmd.append(infile)
    cmd.extend(["--replace", "--to-fls2"])

    run_cmd(cmd)


def sign_fls(flstool, sign, script, output, psi, eblsec):

    cmd = [flstool, "--sign", sign,
                    "--script", script,
                    "--output", output]

    if psi and eblsec:
        cmd.extend(["--psi", psi])
        cmd.extend(["--ebl-sec", eblsec])

    cmd.append("--replace")

    run_cmd(cmd)


def build_fls(unpack_dir, target, variant=None):
    """Build fls flash file out of tfp"""

    sign, target2tag = check_signed_fls(target)
    tag = get_tag(target2tag)
    provdata_zip  = 'provdata_%s.zip' % variant if variant else 'provdata.zip'
    provdata_name = os.path.join(unpack_dir, "RADIO", provdata_zip)
    provdata, provdata_zip = common.UnzipTemp(provdata_name)

    target2file = open(os.path.join(provdata, "fftf_build.opt")).read().strip()
    t2f = init_t2f_dict(target2file)
    flstool = os.path.join(provdata, os.path.basename(t2f["FLSTOOL"]))

    prg = os.path.join(provdata, os.path.basename(t2f["INTEL_PRG_FILE"]))
    out = os.path.join(unpack_dir, "IMAGES", target2tag + '.fls')
    infile = os.path.join(unpack_dir, "IMAGES", target2tag + '.img')
    psi, eblsec = get_psi(provdata, t2f)

    run_fls(flstool, prg, out, tag, infile, psi, eblsec)

    if sign:
        script = os.path.join(provdata, os.path.basename(t2f["SYSTEM_FLS_SIGN_SCRIPT"]))
        out_signed = os.path.join(unpack_dir, "IMAGES", target)

        sign_fls(flstool, out, script, out_signed, psi, eblsec)

    try:
        os.makedirs(os.path.join(t2f["FASTBOOT_IMG_DIR"]))
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(os.path.join(t2f["FASTBOOT_IMG_DIR"])):
            pass
        else: raise

    shutil.copyfile(os.path.join(unpack_dir, "IMAGES", target2tag + '.img'),
                    os.path.join(t2f["FASTBOOT_IMG_DIR"], target2tag + '.bin'))


def build_fls_out(product_out, intermediate_dir, target, outfile, variant=None):
    """Build fls flash file from raw out folder"""

    target2file = open(os.path.join(intermediate_dir, "../", "fftf_build.opt")).read().strip()
    t2f = init_t2f_dict(target2file)

    sign, target2tag = check_signed_fls(target)
    tag = get_tag(target2tag)
    flstool = t2f["FLSTOOL"]

    prg = os.path.join(intermediate_dir, os.path.basename(t2f["INTEL_PRG_FILE"]))

    if sign:
        out = outfile[:-7]
    else:
        out = outfile
    infile = os.path.join(product_out, target2tag + '.img')
    psi, eblsec = get_psi(intermediate_dir, t2f)

    run_fls(flstool, prg, out, tag, infile, psi, eblsec)

    if sign:
        script = t2f["SYSTEM_FLS_SIGN_SCRIPT"]
        sign_fls(flstool, out, script, outfile, psi, eblsec)

def escaped_value(value):
    result = ''
    for char in value:
        result += "%%%02x" % ord(char)
    return result


def get_efi_sig_list(pem_cert, guid_str, name):
    tf = tempfile.NamedTemporaryFile(prefix="pem_cert_to_esl-"+name+"-")
    if pem_cert:
        cmd = ["cert-to-efi-sig-list", "-g", guid_str, pem_cert, tf.name]
        p = common.Run(cmd)
        p.communicate()
        assert p.returncode == 0, "cert-to-efi-sig-list failed"
    tf.seek(os.SEEK_SET, 0)
    return tf


def get_auth_data(timestamp, sign_pair, password, pem_cert, guid_str, name, payload = None):
    esl = get_efi_sig_list(pem_cert, guid_str, name)

    if payload:
        esl.write(payload)
        esl.seek(os.SEEK_SET, 0)

    pem_key = pk8_to_pem(sign_pair + common.OPTIONS.private_key_suffix, password)

    tf = tempfile.NamedTemporaryFile(prefix="auth_file-"+name+"-")
    timestampfmt = "%Y-%m-%d %I:%M:%S"

    cmd = ["sign-efi-sig-list", "-t",
           time.strftime(timestampfmt, time.strptime(time.ctime(timestamp))),
           "-c", sign_pair + common.OPTIONS.public_key_suffix,
           "-g", guid_str, "-k", pem_key.name, name, esl.name, tf.name]
    p = common.Run(cmd)
    p.communicate()
    assert p.returncode == 0, "sign-efi-sig-list failed"
    tf.seek(os.SEEK_SET, 0)
    pem_key.close()
    esl.close()
    data = tf.read()
    tf.close()
    return data


def get_bootloader_list(unpack_dir):
    """ Return an sorted list of the bootloader components by parsing the
        flashfiles_fls.json file. """

    bootloader_list = []
    flashfls_path = os.path.join(unpack_dir, "RADIO", "flashfiles_fls.json")

    with open(flashfls_path, 'r') as flashfls_json:
        data = json.loads(flashfls_json.read())
    for cmd in data['commands']:
        if (cmd['type'] == "fls" and cmd['source'] == "provdatazip"):
            if (cmd['partition'] != 'oem' and cmd['partition'] != 'modem'
                and cmd['partition'] != 'vrl' and (cmd['partition'] not in bootloader_list)):
                bootloader_list.append(cmd['partition'])

    return sorted(bootloader_list)


def get_partition_target_hash(unpack_dir):
    """ Return a hash comprising of the mapping of partition name
        to target name. """

    partition_target = {}
    flashfls_path = os.path.join(unpack_dir, "RADIO", "flashfiles_fls.json")

    with open(flashfls_path, 'r') as flashfls_json:
        data = json.loads(flashfls_json.read())
    for cmd in data['commands']:
        if (cmd['type'] == "fls"):
            # FIXME We do not compare the image partitions with
            # smp_profiling images in the TFP assuming smp_profiling
            # images are never flashed on the device being verified
            # Remove this assumption.

            if (cmd.get('core') != 'smp_profiling'):
                partition_target[cmd['partition']] = cmd['target']

    return partition_target


def get_provdata_variants(unpack_dir):
    """ Return a list of variants for a TFP. """

    variants = []
    working_path = os.path.join(unpack_dir, "RADIO")
    # Use regex analysis of provdata files to determine current variants
    regex = re.compile('provdata_(?P<variant>\w+).zip')
    for f in os.listdir(working_path):
        m = regex.match(os.path.basename(f))
        if m and m.group('variant'):
            variants.append(m.group('variant'))
    return variants


def CheckIfSocEFI(unpack_dir, variant):
    """ Non-EFI SOC (Sofia and its variants), have fftf_build.opt file
    in the provdata which is used to check if the DUT is efi or not.
    If the variant is not provided as an option, get the variant list
    and read the fftf_build.opt in the first variant in the list.
    For Sofia SOC also use SECPACK_IN_SLB = true to check if is sofialte """

    if not variant:
        variants_list = get_provdata_variants(unpack_dir)
        if not variants_list:
            provdata_name = os.path.join(unpack_dir, "RADIO", "provdata" + ".zip")
        else:
            variant = variants_list[0]
            provdata_name = os.path.join(unpack_dir, "RADIO", "provdata_" + variant + ".zip")
    else:
        provdata_name = os.path.join(unpack_dir, "RADIO", "provdata_" + variant + ".zip")

    provdata = zipfile.ZipFile(provdata_name, 'r')
    fftf_build_file = 'fftf_build.opt'

    if (fftf_build_file in provdata.namelist()):
        target2file = provdata.read(fftf_build_file)
        t2f = init_t2f_dict(target2file)
        provdata.close()
        if (t2f["SOC_FIRMWARE_TYPE"] == "slb"):
           if (t2f["SECPACK_IN_SLB"] == "true"):
               return False, True
           else:
               return False, False
    provdata.close()
    return True, False

def GenerateBootloaderSecbin(unpack_dir, variant):
    """ Generate bootloader with secpack for Non-EFI(example Sofialte); The partitions are
    obtained from get_bootloader_list() in GetBootloaderImagesfromFls.
    use tool binary_merge to generate Merged.secbin with SecureBlock.bin + LoadMap.bin
    """

    for current_file in os.listdir(unpack_dir):
        if fnmatch.fnmatch(current_file, '*LoadMap0.bin'):
             loader_mapdatafile = current_file

    assert loader_mapdatafile is not None, "Error in extracting the LoadMap.bin"
    for current_file in os.listdir(unpack_dir):
        if fnmatch.fnmatch(current_file, '*SecureBlock.bin'):
             loader_scublockfile = current_file

    assert loader_scublockfile is not None, "Error in extracting the SecureBlock.bin"
    binary_merge = "hardware/intel/sofia_lte-fls/tools/binary_merge"
    cmd = [binary_merge, "-o", os.path.join(unpack_dir, "Merged.secbin"),
                         "-b 1 -p 0"]
    cmd.append(os.path.join(unpack_dir, loader_scublockfile))
    cmd.append(os.path.join(unpack_dir, loader_mapdatafile))
    print "execute 3.command: {}".format(' '.join(cmd))
    try:
        p = common.Run(cmd)
    except Exception as exc:
        print "Error: Unable to execute command: {}".format(' '.join(cmd))
        raise exc
    p.communicate()
    assert p.returncode == 0, "binary_merge failed"

def GetBootloaderImagesfromFls(unpack_dir, variant=None):
    """ Non-EFI bootloaders (example Sofia and its variants), comprise of
    various partitions. The partitions are obtained from get_bootloader_list().
    Extract and return the *LoadMap.bin files from the *.fls files. """

    bootloader_list = get_bootloader_list(unpack_dir)
    if variant:
        provdata_name = os.path.join(unpack_dir, "RADIO", "provdata_" + variant + ".zip")
    else:
        provdata_name = os.path.join(unpack_dir, "RADIO", "provdata" + ".zip")
    provdata, provdata_zip = common.UnzipTemp(provdata_name)
    additional_data_hash = collections.OrderedDict()
    partition_to_target = get_partition_target_hash(unpack_dir)

    platform_efi, platform_sflte = CheckIfSocEFI(unpack_dir, variant)

    for loader_partition in bootloader_list:
        curr_loader = partition_to_target[loader_partition]
        loader_filepath = os.path.join(provdata, curr_loader)
        extract = tempfile.mkdtemp(prefix=curr_loader)
        common.OPTIONS.tempfiles.append(extract)
        flstool = os.path.join(provdata, "FlsTool")
        cmd = [flstool, "-x", loader_filepath, "-o", extract]
        try:
            p = common.Run(cmd)
        except Exception as exc:
            print "Error: Unable to execute command: {}".format(' '.join(cmd))
            raise exc
        p.communicate()
        assert p.returncode == 0, "FlsTool failed to extract LoadMap.bin"
        if platform_sflte :
           #for psi: it is verfied by bootrom,
           #so no need add secpack header, need bypass;
           #for bootloader: the combinded images in this partition already has secpack
           #so no need add secpack header, need bypass
           if (loader_partition == 'psi') or (loader_partition == 'bootloader'):
               for current_file in os.listdir(extract):
                  if fnmatch.fnmatch(current_file, '*LoadMap0.bin'):
                      loader_datafile = current_file
           else:
               #generate Merged.secbin with tool binary_merge
               GenerateBootloaderSecbin(extract, variant)
               for current_file in os.listdir(extract):
                  if fnmatch.fnmatch(current_file, 'Merged.secbin'):
                      loader_datafile = current_file
        else:
           for current_file in os.listdir(extract):
               if fnmatch.fnmatch(current_file, '*LoadMap0.bin'):
                    loader_datafile = current_file

        loader_abspath = os.path.join(extract ,loader_datafile)
        assert loader_datafile is not None, "Error in extracting the LoadMap.bin"
        loader_file = open(loader_abspath)
        loader_data = loader_file.read()
        additional_data_hash[loader_partition] = loader_data
        loader_file.close()

    return additional_data_hash
