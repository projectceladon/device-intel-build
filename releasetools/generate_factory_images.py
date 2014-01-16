#!/usr/bin/env python
"""

Generate archive for fastboot factory installations.

"""

from sys import exit, stderr
from argparse import ArgumentParser
from tempfile import gettempdir
from tarfile import DIRTYPE, TarInfo, open as TarOpen
from hashlib import sha1
from os import path, chmod, rename, remove
from time import time
from subprocess import check_call

_FLASHALL_FILENAME = "flash-all.sh"
_FLASHBASE_FILENAME = "flash-base.sh"
# chmod (octal) -rwxr-x--x
_PERMS = 0751
_FLASH_HEADER = """#!/bin/sh

# Copyright 2012 The Android Open Source Project
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
_FLASH_FOOTER = "\n"
_FASTBOOT_REBOOT_COMMAND = "reboot-bootloader"
_WIN_FLASHALL_FILENAME = "flash-all.bat"
_WIN_FLASH_HEADER = """@ECHO OFF
:: Copyright 2012 The Android Open Source Project
::
:: Licensed under the Apache License, Version 2.0 (the "License");
:: you may not use this file except in compliance with the License.
:: You may obtain a copy of the License at
::
::      http://www.apache.org/licenses/LICENSE-2.0
::
:: Unless required by applicable law or agreed to in writing, software
:: distributed under the License is distributed on an "AS IS" BASIS,
:: WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
:: See the License for the specific language governing permissions and
:: limitations under the License.

PATH=%PATH%;\"%SYSTEMROOT%\System32\"
"""
_WIN_FLASH_FOOTER = """
echo Press any key to exit...
pause >nul
exit

"""


def Checksum(filename):
    """Find SHA-1 checksum"""
    with open(filename) as fid:

        # Create sha-1 checksum
        h = sha1()
        h.update(fid.read())

        fid.close()

        return h.hexdigest()


def FastbootFlashCommand(flash_type, image, optional=None):
    """Create fastboot command"""
    # Fastboot Command
    text = "fastboot "
    if optional:
        text += optional + " "
    text += "flash " + str(flash_type) + " " + path.basename(image) + "\n"
    # Reboot Command
    text += "fastboot "
    if optional:
        text += optional + " "
    text += _FASTBOOT_REBOOT_COMMAND + "\n"

    return text


def FastbootUpdateCommand(archive, optional=None, erase=None):
    """Create fastboot update command"""
    text = "fastboot "

    if optional:
        text += optional + " "

    if erase:
        text += "-w "

    text += "update " + path.basename(archive) + "\n"

    return text


def FastbootSleepCommand(sleep):
    """Create fastboot sleep command"""
    return "sleep " + str(sleep) + "\n"


def FastbootWinPingCommand(num_ping):
    """Create Windows fastboot ping command"""
    return "ping -n {} 127.0.0.1 >nul\n".format(num_ping)


def ConvertToDOSFormat(filename):
    """Convert to DOS file format"""
    check_call(["unix2dos", filename])


def CreateWinFlashScript(filename, flash_list,
                         num_ping=5, fastboot_args=None, fastboot_erase=None):
    """Generate flash batch file"""
    filename = path.join(gettempdir(), filename)

    # Create Script
    with open(filename, "w") as fid:
        fid.write(_WIN_FLASH_HEADER)

        # Flash Commands
        for name, location in flash_list:
            if name == "update":
                fid.write(FastbootUpdateCommand(location,
                                                fastboot_args,
                                                fastboot_erase))
            else:
                fid.write(FastbootFlashCommand(name,
                                               location,
                                               fastboot_args))
                fid.write(FastbootWinPingCommand(num_ping))

        # Footer
        fid.write(_WIN_FLASH_FOOTER)

    # Change Permissions
    chmod(filename, _PERMS)

    return filename


def CreateFlashScript(filename, flash_list,
                      sleeptime=5, fastboot_args=None, fastboot_erase=None):
    """Generate flash-all.sh"""
    filename = path.join(gettempdir(), filename)

    # Create Script
    with open(filename, "w") as fid:
        fid.write(_FLASH_HEADER)

        # Flash Commands
        for flash in flash_list:
            if flash[0] == "update":
                fid.write(FastbootUpdateCommand(flash[1],
                                                fastboot_args,
                                                fastboot_erase))
            else:
                fid.write(FastbootFlashCommand(flash[0],
                                               flash[1],
                                               fastboot_args))
                fid.write(FastbootSleepCommand(sleeptime))

        # Footer
        fid.write(_FLASH_FOOTER)

    # Change Permissions
    chmod(filename, _PERMS)

    return filename


def GetTarInfo(filename, filetype=DIRTYPE, mode=0755):
    """Create information for tar files"""
    tarinfo = TarInfo(path.basename(filename))
    tarinfo.type = filetype
    tarinfo.mode = mode
    tarinfo.mtime = time()
    return tarinfo


def RequireFile(filename):
    """Ensure file exists"""
    if not path.exists(filename):
        raise Usage("Cannot find " + filename)


def FlashListCreate(bootloader=None, radio=None, fastboot=None, update=None):
    """Create List of fastboot flash images"""
    partitions = []

    if bootloader:
        RequireFile(bootloader)
        partitions.append(("bootloader", bootloader))
    if radio:
        RequireFile(radio)
        partitions.append(("radio", radio))
    if fastboot:
        RequireFile(fastboot)
        partitions.append(("fastboot", fastboot))
    if update:
        RequireFile(update)
        partitions.append(("update", update))

    return partitions


def FlashListRemoveName(flash_list, remove):
    """Remove flash partition from flash list"""
    for index, (name, filename) in enumerate(flash_list):
        if name == remove:
            del flash_list[index]
            break


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


class CommandlineParser(ArgumentParser):
    """Enhanced argument parser for command line"""
    def __init__(self):
        super(CommandlineParser, self).__init__()
        self.description = __doc__

    def error(self, message):
        print >>stderr, "ERROR: {}".format(message)
        print >>stderr, "\n------\n"
        self.print_help()
        exit(2)


def main():
    """Main"""
    parser = CommandlineParser()
    parser.add_argument('--product', required=True,
                        help="Product name, e.g. hammerhead")
    parser.add_argument('--release', required=True,
                        help="Release name, e.g. krt16m")
    parser.add_argument('-b', '--bootloader',
                        help="Bootloader image for fastboot flash")
    parser.add_argument('-r', '--radio',
                        help="Radio image for fastboot flash")
    parser.add_argument('-f', '--fastboot',
                        help="Fastboot image for fastboot flash")
    parser.add_argument('-u', '--update-archive',
                        help="Zipped images for fastboot update")
    parser.add_argument('-i', '--input', nargs="+",
                        help="Add additional files to archive")
    parser.add_argument('--fastboot-args',
                        default=None,
                        help="Add additional fastboot arguments, " +
                             "e.g -t 192.168.42.1")
    parser.add_argument('-e', '--erase',
                        action='store_true',
                        help="Erase partitions before fastboot update")
    parser.add_argument('-s', '--sleeptime',
                        type=int, default=5,
                        help="Sleep in seconds for fastboot reboot, default=5")
    parser.add_argument('--no-checksum',
                        action='store_true', default=False,
                        help="Remove SHA-1 checksum from archive filename")
    parser.add_argument('-o', '--output',
                        help="Output directory for archived factory scripts")
    args = parser.parse_args()

    # Create Flash List
    flash_images = FlashListCreate(bootloader=args.bootloader,
                                   radio=args.radio,
                                   fastboot=args.fastboot,
                                   update=args.update_archive)
    if not flash_images:
        raise Usage("No flash images provided.")

    # Archive Name
    archive_name = "{}-{}-factory".format(args.product, args.release)
    archive_name = archive_name.lower()
    archive_name = path.join(args.output, archive_name)

    # Create Archive
    print "Creating archive: " + archive_name
    tar = TarOpen(archive_name, "w:gz")

    # Archive Images
    for name, filename in flash_images:
        print "Archiving " + filename
        tar.add(filename, arcname=path.basename(filename))

    # Archive Additional
    if args.input:
        for f in args.input:
            print "Archiving " + f
            RequireFile(f)
            tar.add(f, arcname=path.basename(f))

    # Archive flash-all.sh
    print "Archiving " + _FLASHALL_FILENAME
    filename = CreateFlashScript(_FLASHALL_FILENAME,
                                 flash_images,
                                 args.sleeptime,
                                 args.fastboot_args,
                                 args.erase)
    tar.add(filename, arcname=path.basename(filename))
    remove(filename)

    # Archive flash-all.bat
    print "Archiving " + _WIN_FLASHALL_FILENAME
    filename = CreateWinFlashScript(_WIN_FLASHALL_FILENAME,
                                    flash_images,
                                    args.sleeptime,
                                    args.fastboot_args,
                                    args.erase)
    print filename
    ConvertToDOSFormat(filename)
    tar.add(filename, arcname=path.basename(filename))
    remove(filename)

    # Archive flash-base.sh
    print "Archiving " + _FLASHBASE_FILENAME
    FlashListRemoveName(flash_images, "update")
    filename = CreateFlashScript(_FLASHBASE_FILENAME,
                                 flash_images,
                                 sleeptime=args.sleeptime,
                                 fastboot_args=args.fastboot_args)
    tar.add(filename, arcname=path.basename(filename))
    remove(filename)

    # Close Archive
    tar.close()

    if not args.no_checksum:
        # Calculate SHA-1 Checksum
        sha1sum = Checksum(archive_name)
        print "Checksum: " + sha1sum

        # Rename Archive
        rename(archive_name, archive_name + "-" + sha1sum[:8] + ".tgz")
    else:
        rename(archive_name, archive_name + ".tgz")

    print "Done."

if __name__ == "__main__":
    try:
        exit(main())
    except Usage, err:
        print >>stderr, "ERROR: {}".format(err.msg)
        print >>stderr, "       for help use --help"
        exit(2)
