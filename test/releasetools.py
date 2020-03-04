import common
import fnmatch
import os
import sys
import tempfile
import subprocess
import zipfile
import json
import hashlib
import os, errno
import shlex
import shutil
import imp
import time
import collections
import time
import re
import random

from io import StringIO

sys.path.append("device/intel/build/releasetools")
import intel_common

_SIMG2IMG = "out/host/linux-x86/bin/simg2img"
_FASTBOOT = "out/host/linux-x86/bin/fastboot"
_STRINGS = "out/host/linux-x86/poky/sysroots/x86_64-pokysdk-linux/usr/bin/x86_64-poky-linux/x86_64-poky-linux-strings"
_VERIFYTOOL = "device/intel/build/test/verify_from_ota"
OPTIONS = common.OPTIONS
need_verify = 1
verify_multiboot = None
multiboot_patchinfo = None
tos_patchinfo = None
vbmeta_patchinfo = None
verify_vbmeta = None
verify_recovery = None
verify_acpi = None
verify_acpio = None
verify_product = None

def hash_sparse_ext4_image(image_name):

  print("TFP: ", image_name)
  t = tempfile.NamedTemporaryFile(delete=False)
  OPTIONS.tempfiles.append(t.name)
  t.close()

  subprocess.check_call([_SIMG2IMG, image_name, t.name])
  remain = os.path.getsize(t.name)
  fd = open(t.name)
  hc = hashlib.sha1()

  while (remain):
      data = fd.read(1024 * 1024)
      hc.update(data)
      remain = remain - len(data)

  print("system hash", hc.hexdigest())
  fd.close()
  return hc.hexdigest()


def GetBootloaderImagesfromFls(unpack_dir, variant=None):
  """ ABL bootloaders, comprise of
  various partitions. The partitions are fixed """
  global verify_multiboot, verify_recovery, verify_vbmeta
  global verify_acpi, verify_acpio, verify_product

  additional_data_hash = collections.OrderedDict()
  #need get boot/recovery/system data first
  curr_loader = "bootloader.img"
  loader_filepath = os.path.join(unpack_dir, "RADIO", curr_loader)
  if not os.path.exists(loader_filepath):
      print("Can't find ", loader_filepath)
      print("GetBootloaderImagesfromFls failed")
      return
  loader_file = open(loader_filepath)
  loader_data = loader_file.read()
  additional_data_hash['bootloader'] = loader_data
  loader_file.close()
  strings_out = subprocess.check_output([_STRINGS, loader_filepath], stderr=subprocess.STDOUT);
  for firmware in strings_out.split('\n'):
      if "rel." in firmware:
          firmware_pattern=re.compile(r'(rel.\d+)(.*-(HF|hf)\d+\h*)?')
          additional_data_hash['firmware'] = re.search(firmware_pattern,firmware).group()
          break;

  #need get boot/recovery/system data first
  curr_loader = "boot.img"
  loader_filepath = os.path.join(unpack_dir, "IMAGES", curr_loader)
  if not os.path.exists(loader_filepath):
      print("Can't find ", loader_filepath)
      print("GetBootloaderImagesfromFls failed")
      return
  loader_file = open(loader_filepath)
  loader_data = loader_file.read()
  additional_data_hash['boot'] = loader_data
  loader_file.close()

  if verify_recovery is not None:
      curr_loader = "recovery.img"
      loader_filepath = os.path.join(unpack_dir, "IMAGES", curr_loader)
      if not os.path.exists(loader_filepath):
          print("Can't find ", loader_filepath)
          print("GetBootloaderImagesfromFls failed")
          return
      loader_file = open(loader_filepath)
      loader_data = loader_file.read()
      additional_data_hash['recovery'] = loader_data
      loader_file.close()

  if verify_vbmeta is not None:
      curr_loader = "vbmeta.img"
      loader_filepath = os.path.join(unpack_dir, "IMAGES", curr_loader)
      if not os.path.exists(loader_filepath):
          print("Can't find ", loader_filepath)
          print("GetBootloaderImagesfromFls failed")
          return
      loader_file = open(loader_filepath)
      loader_data = loader_file.read()
      additional_data_hash['vbmeta'] = loader_data
      loader_file.close()

  curr_loader = "system.img"
  loader_filepath = os.path.join(unpack_dir, "IMAGES", curr_loader)
  if not os.path.exists(loader_filepath):
      print("Can't find ", loader_filepath)
      print("GetBootloaderImagesfromFls failed")
      return
  additional_data_hash['system'] = str(hash_sparse_ext4_image(loader_filepath))

  if verify_multiboot is not None:
    curr_loader = "multiboot.img"
    loader_filepath = os.path.join(unpack_dir, "RADIO", curr_loader)
    if os.path.exists(loader_filepath):
        loader_file = open(loader_filepath)
        loader_data = loader_file.read()
        additional_data_hash['multiboot'] = loader_data
        loader_file.close()
    curr_loader = "tos.img"
    loader_filepath = os.path.join(unpack_dir, "RADIO", curr_loader)
    if os.path.exists(loader_filepath):
        loader_file = open(loader_filepath)
        loader_data = loader_file.read()
        additional_data_hash['tos'] = loader_data
        loader_file.close()

  curr_loader = "vendor.img"
  loader_filepath = os.path.join(unpack_dir, "IMAGES", curr_loader)
  if not os.path.exists(loader_filepath):
      print("Can't find ", loader_filepath)
      print("GetBootloaderImagesfromFls failed")
      return
  additional_data_hash['vendor'] = str(hash_sparse_ext4_image(loader_filepath))

  if verify_acpi is not None:
      curr_loader = "acpi.img"
      loader_filepath = os.path.join(unpack_dir, "RADIO", curr_loader)
      if not os.path.exists(loader_filepath):
          print("Can't find ", loader_filepath)
          print("GetBootloaderImagesfromFls failed")
          return
      loader_file = open(loader_filepath)
      loader_data = loader_file.read()
      additional_data_hash['acpi'] = loader_data
      loader_file.close()

  if verify_acpio is not None:
      curr_loader = "acpio.img"
      loader_filepath = os.path.join(unpack_dir, "RADIO", curr_loader)
      if not os.path.exists(loader_filepath):
          print("Can't find ", loader_filepath)
          print("GetBootloaderImagesfromFls failed")
          return
      loader_file = open(loader_filepath)
      loader_data = loader_file.read()
      additional_data_hash['acpio'] = loader_data
      loader_file.close()

  if verify_product is not None:
      curr_loader = "product.img"
      loader_filepath = os.path.join(unpack_dir, "IMAGES", curr_loader)
      if not os.path.exists(loader_filepath):
          print("Can't find ", loader_filepath)
          print("GetBootloaderImagesfromFls failed")
          return
      additional_data_hash['product'] = str(hash_sparse_ext4_image(loader_filepath))

  return additional_data_hash

def Get_verifydata(info,infoinput):
  print("Trying to get verify data...")
  variant = None

  for app in [_SIMG2IMG, _FASTBOOT, _VERIFYTOOL, _STRINGS]:
      if not os.path.exists(app):
          print("Can't find", app)
          print("Get_verifydata failed")
          return

  print("Extracting bootloader archive...")
  additional_data = GetBootloaderImagesfromFls(infoinput,None)
  if not additional_data:
    print("additional_data is None")
    return
  bootloader_sizes = ""
  imghash_value = "..."
  imghash_bootloader = ""

  for imgname, imgdata in additional_data.items():
      print("OTA verify with ", imgname)
      if imgname != 'system' and imgname != 'boot' and imgname != 'recovery' and imgname != 'vbmeta' \
          and imgname != 'vendor' and imgname != 'multiboot' and imgname != 'tos' and imgname != 'firmware' \
          and imgname != 'acpi' and imgname != 'acpio' and imgname != 'product':
          bootloader_sizes += ":" + str(len(imgdata))
      if imgname != 'system' and imgname != 'vendor' and imgname != 'firmware' and imgname != 'product':
          imghash_value += "\n(bootloader) target: /" + str(imgname)
          imghash_value += "\n(bootloader) hash: " + str(hashlib.sha1(imgdata).hexdigest())
      if imgname == 'system' or imgname == 'vendor' or imgname == 'product':
          imghash_value += "\n(bootloader) target: /" + str(imgname)
          imghash_value += "\n(bootloader) hash: " + str(imgdata)
      if imgname == 'firmware':
          imghash_value += "\n(bootloader) target: /" + str(imgname)
          imghash_value += "\n(bootloader) version: " + imgdata
  imghash_value += imghash_bootloader + "\n"

  common.ZipWriteStr(info.output_zip, "verify/fastbootcmd.txt", bootloader_sizes)
  common.ZipWriteStr(info.output_zip, "verify/hashesfromtgt.txt", imghash_value)
  #write fastboot tool
  f = open(_FASTBOOT, "rb")
  fbbin = f.read()
  common.ZipWriteStr(info.output_zip, "verify/fastboot", fbbin, perms=0o755)
  f.close()
  #Save verify_from_ota script to OTA package
  f = open(_VERIFYTOOL, "r")
  data = f.read()
  common.ZipWriteStr(info.output_zip, "verify/verify_from_ota", data, perms=0o755)
  f.close()

def WriteMultiboot(info, multiboot_img):
  common.ZipWriteStr(info.output_zip, "multiboot.img", multiboot_img)
  try:
    info.script.WriteRawImage("/multiboot", "multiboot.img")
  except (IOError, KeyError):
    print("no /multiboot partition in target_files; skipping install")

def WriteTos(info, tos_img):
  common.ZipWriteStr(info.output_zip, "tos.img", tos_img)
  try:
    info.script.WriteRawImage("/tos", "tos.img")
  except (IOError, KeyError):
    print("no /tos partition in target_files; skipping install")

def WriteVbmeta(info, vbmeta_img):
  common.ZipWriteStr(info.output_zip, "vbmeta.img", vbmeta_img)
  try:
    info.script.WriteRawImage("/vbmeta", "vbmeta.img")
  except (IOError, KeyError):
    print("no /vbmeta partition in target_files; skipping install")

def WriteBldr(info, bootloader_img):
  common.ZipWriteStr(info.output_zip, "bootloader.img", bootloader_img)
  info.script.WriteRawImage("/bootloader", "bootloader.img")
  info.script.script.append('capsule_abl("m1:@0");')

def IncrementalOTA_VerifyEnd(info):
  global multiboot_patchinfo
  global tos_patchinfo

  fstab = info.script.info.get("fstab", None)
  try:
    if fstab['/multiboot'].device:
      multibootimg_type, multibootimg_device = common.GetTypeAndDevice("/multiboot", OPTIONS.info_dict)
      verbatim_targets, m_patch_list, output_files = \
              intel_common.ComputeBinOrImgPatches(OPTIONS.source_tmp,
                                                  OPTIONS.target_tmp, "multiboot.img")
      if output_files is None:
        print("multiboot.img is none, skipping install")
      else:
        print("multiboot.img is exist. Add the patch.")
        if not verbatim_targets and m_patch_list:
          (tf,sf) = m_patch_list
          info.script.PatchCheck("%s:%s:%d:%s:%d:%s" %
                                 (multibootimg_type, multibootimg_device, sf.size,
                                  sf.sha1, tf.size, tf.sha1))
          multiboot_patchinfo = (multibootimg_type, multibootimg_device, sf, tf)
          common.ZipWriteStr(info.output_zip, "patch/multiboot.img.p", output_files)
    if fstab['/tos'].device:
      tosimg_type, tosimg_device = common.GetTypeAndDevice("/tos", OPTIONS.info_dict)
      verbatim_targets, m_patch_list, output_files = \
              intel_common.ComputeBinOrImgPatches(OPTIONS.source_tmp,
                                                  OPTIONS.target_tmp, "tos.img")
      if output_files is None:
        print("tos.img is none, skipping install")
      else:
        print("tos.img is exist. Add the patch.")
        if not verbatim_targets and m_patch_list:
          (tf,sf) = m_patch_list
          info.script.PatchCheck("%s:%s:%d:%s:%d:%s" %
                                 (tosimg_type, tosimg_device, sf.size,
                                  sf.sha1, tf.size, tf.sha1))
          tos_patchinfo = (tosimg_type, tosimg_device, sf, tf)
          common.ZipWriteStr(info.output_zip, "patch/tos.img.p", output_files)
    if fstab['/vbmeta'].device:
      vbmetaimg_type, vbmetaimg_device = common.GetTypeAndDevice("/vbmeta", OPTIONS.info_dict)
      verbatim_targets, m_patch_list, output_files = \
               intel_common.ComputeBinOrImgPatches(OPTIONS.source_tmp,
                                                   OPTIONS.target_tmp, "vbmeta.img")
      if output_files is None:
        print("vbmeta.img is none, skipping install")
      else:
        print("vbmeta.img is exist. Add the patch.")
        if not verbatim_targets and m_patch_list:
          (tf,sf) = m_patch_list
          info.script.PatchCheck("%s:%s:%d:%s:%d:%s" %
                                 (vbmetaimg_type, vbmetaimg_device, sf.size,
                                  sf.sha1, tf.size, tf.sha1))
          vbmeta_patchinfo = (vbmetaimg_type, vbmetaimg_device, sf, tf)
          common.ZipWriteStr(info.output_zip, "patch/vbmeta.img.p", output_files)
  except (IOError, KeyError):
    print("No multiboot/tos/vbmeta partition in iOTA Verify")

def FullOTA_InstallEnd(info):
  global verify_multiboot, verify_recovery, verify_vbmeta;
  global verify_acpi, verify_acpio, verify_product;

  try:
    bootloader_img = info.input_zip.read("RADIO/bootloader.img")
  except KeyError:
    print("no bootloader.img in target_files; skipping install")
  else:
    print("Add update for bootloader")
    WriteBldr(info, bootloader_img)

    try:
      multiboot_img = info.input_zip.read("RADIO/multiboot.img")
    except (IOError, KeyError):
      print("no multiboot.img in target target_files; skipping install")
    else:
      fstab = info.script.info.get("fstab", None)
      try:
        if fstab['/multiboot'].device:
          print("multiboot partition exist and multiboot.img changed; adding it")
          WriteMultiboot(info, multiboot_img)
          verify_multiboot = need_verify
      except (IOError, KeyError):
        print("No multiboot partition")

    try:
      tos_img = info.input_zip.read("RADIO/tos.img")
    except (IOError, KeyError):
      print("no tos.img in target target_files; skipping install")
    else:
      fstab = info.script.info.get("fstab", None)
      try:
        if fstab['/tos'].device:
          print("tos partition exist and tos.img changed; adding it")
          WriteTos(info, tos_img)
          verify_multiboot = need_verify
      except (IOError, KeyError):
        print("No tos partition")

    try:
      vbmeta_img = info.input_zip.read("IMAGES/vbmeta.img")
    except (IOError, KeyError):
      print("no vbmeta.img in target target_files; skipping install")
    else:
      fstab = info.script.info.get("fstab", None)
      try:
        if fstab['/vbmeta'].device:
          print("vbmeta partition exist and vbmeta.img changed; adding it")
          verify_vbmeta = need_verify
          WriteVbmeta(info, vbmeta_img)
      except (IOError, KeyError):
        print("No vbmeta partition")

    try:
      recovery_img = info.input_zip.read("IMAGES/recovery.img")
    except (IOError, KeyError):
      print("no recovery.img in target target_files; skipping install")
    else:
      fstab = info.script.info.get("fstab", None)
      try:
        if fstab['/recovery'].device:
          print("recovery partition exist and recovery.img changed; adding it")
          verify_recovery = need_verify
      except (IOError, KeyError):
        print("No recovery partition")

    try:
      acpi_img = info.input_zip.read("RADIO/acpi.img")
      verify_acpi = need_verify
    except (IOError, KeyError):
      print("no acpi.img in target target_files; skipping install")

    try:
      acpio_img = info.input_zip.read("RADIO/acpio.img")
      verify_acpio = need_verify
    except (IOError, KeyError):
      print("no acpio.img in target target_files; skipping install")

    try:
      product_img = info.input_zip.read("IMAGES/product.img")
      verify_product = need_verify
    except (IOError, KeyError):
      print("no product.img in target target_files; skipping install")

    Get_verifydata(info, info.input_tmp)

def IncrementalOTA_InstallEnd(info):
  global verify_multiboot
  try:
    target_bootloader_img = info.target_zip.read("RADIO/bootloader.img")
    try:
      source_bootloader_img = info.source_zip.read("RADIO/bootloader.img")
    except KeyError:
      source_bootloader_img = None

    if source_bootloader_img == target_bootloader_img:
      print("bootloader.img unchanged; skipping")
    else:
      print("bootloader.img changed; adding it")
      WriteBldr(info, target_bootloader_img)

    try:
      multiboot_img = info.target_zip.read("RADIO/multiboot.img")
    except (IOError, KeyError):
      print("no multiboot.img in target target_files; skipping install")
    else:
      fstab = info.script.info.get("fstab", None)
      try:
        if fstab['/multiboot'].device:
          print("multiboot partition exist and multiboot.img changed; adding it")
          multibootimg_type, multibootimg_device, sf, tf = multiboot_patchinfo
          info.script.ApplyPatch("%s:%s:%d:%s:%d:%s" % (multibootimg_type, multibootimg_device, sf.size,
                                                        sf.sha1, tf.size, tf.sha1),
                                 "-", tf.size, tf.sha1, sf.sha1,
                                 "patch/multiboot.img.p")
          verify_multiboot = need_verify
      except (IOError, KeyError):
        print("No multiboot partition")

    try:
      tos_img = info.target_zip.read("RADIO/tos.img")
    except (IOError, KeyError):
      print("no tos.img in target target_files; skipping install")
    else:
      fstab = info.script.info.get("fstab", None)
      try:
        if fstab['/tos'].device:
          print("tos partition exist and tos.img changed; adding it")
          tosimg_type, tosimg_device, sf, tf = tos_patchinfo
          info.script.ApplyPatch("%s:%s:%d:%s:%d:%s" % (tosimg_type, tosimg_device, sf.size,
                                                        sf.sha1, tf.size, tf.sha1),
                                 "-", tf.size, tf.sha1, sf.sha1,
                                 "patch/tos.img.p")
          verify_multiboot = need_verify
      except (IOError, KeyError):
        print("No tos partition")

    try:
      vbmeta_img = info.target_zip.read("IMAGES/vbmeta.img")
    except (IOError, KeyError):
      print("no vbmeta.img in target target_files; skipping install")
    else:
      fstab = info.script.info.get("fstab", None)
      try:
        if fstab['/vbmeta'].device:
          print("vbmeta partition exist and vbmeta.img changed; adding it")
          vbmetaimg_type, vbmetaimg_device, sf, tf = vbmeta_patchinfo
          info.script.ApplyPatch("%s:%s:%d:%s:%d:%s" % (vbmetaimg_type, vbmetaimg_device, sf.size,
                                                        sf.sha1, tf.size, tf.sha1),
                                 "-", tf.size, tf.sha1, sf.sha1,
                                 "patch/tos.img.p")
      except (IOError, KeyError):
        print("No vbmeta partition")

    Get_verifydata(info, OPTIONS.target_tmp)
  except KeyError:
    print("no bootloader.img in target target_files; skipping install")

