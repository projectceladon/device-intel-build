#!/usr/bin/env python

import sys
import os
import re
from optparse import OptionParser

informative_message = "Proprietary device-specific files must be stored in vendor partition. \n\
LOCAL_PROPRIETARY_MODULE := true should be used in module definition. \n\
Path (LOCAL_MODULE_PATH) will be defined by Android build system using LOCAL_MODULE_CLASS information. \n\
 \n\
-----------------------------------------------------------------------------------------------------\n\
|LOCAL_MODULE_CLASS | vendor partition activated     | vendor partition NOT activated               |\n\
|---------------------------------------------------------------------------------------------------|\n\
|EXECUTABLES        | /vendor/bin/                   | /system/vendor/bin/                          |\n\
|SHARED_LIBRARIES   | /vendor/lib/ or /vendor/lib64/ | /system/vendor/lib/ or /system/vendor/lib64/ |\n\
|JAVA_LIBRARIES     | /vendor/framework              | /system/vendor/framework                     |\n\
|APPS               | /vendor/app                    | /system/vendor/app                           |\n\
|ETC                | /vendor/etc                    | /system/vendor/etc                           |\n\
-----------------------------------------------------------------------------------------------------\n\
 \n\
If binary location cannot be defined by Android build system, LOCAL_MODULE_PATH should be defined using TARGET_OUT_VENDOR.\n\
 \n\
PRODUCT_COPY_FILES must be avoided to be compliant with Android build system requirements. \n\
If PRODUCT_COPY_FILES are used, usage of TARGET_COPY_OUT_VENDOR is required \n\
 \n\
Exemples of module: \n\
    include $(CLEAR_VARS) \n\
    LOCAL_MODULE := module_intel \n\
    LOCAL_MODULE_CLASS := ETC \n\
    LOCAL_MODULE_OWNER := intel \n\
    LOCAL_SRC_FILES := file \n\
    LOCAL_PROPRIETARY_MODULE := true \n\
    include $(BUILD_PREBUILT) \n\
 \n\
    include $(CLEAR_VARS) \n\
    LOCAL_MODULE := module_intel_fw \n\
    LOCAL_MODULE_CLASS := ETC \n\
    LOCAL_MODULE_OWNER := intel \n\
    LOCAL_SRC_FILES := fw \n\
    LOCAL_PROPRIETARY_MODULE := true \n\
    LOCAL_MODULE_PATH := $(TARGET_OUT_VENDOR) \n\
    LOCAL_MODULE_RELATIVE_PATH := firmware \n\
    include $(BUILD_PREBUILT) \n\
 \n\
https://wiki.ith.intel.com/display/ANDROIDSI/Vendor \n"

informative_message_light = "https://wiki.ith.intel.com/display/ANDROIDSI/Vendor \n"

warning_message1 = "WARNING: Prefer usage of LOCAL_PROPRIETARY_MODULE"
warning_message2 = "WARNING: Module will not be in vendor !"
separative_line = "================================================================================"


def get_sections(f, out):
    out.append("##########MAKEFILE: " + f + " ##########")
    # Use "with" so the file will automatically be closed
    with open(f, "r") as fobj:
        text = fobj.read()

    pattern = re.compile(r'(include \S+CLEAR_VARS\S\s*)(.*?)\s*(include \S+BUILD_\w+)', re.DOTALL)

    matches = pattern.findall(text)
    out.append(matches)

    return matches, out


def print_vendor(message):
    print "[NOT IN VENDOR] " + message


def warning_message(err_num, f, message, section):
    print separative_line
    print_vendor(str(err_num)+'/ '+f+' : '+message)


def light_message(makefile, section):
    module = get_module(section)
    print_vendor("In "+makefile+" module "+str(module)+" will not be in vendor")


def search_string(light, tup, f, nb_err, out):
    sections, out = get_sections(f, out)
    for s in sections:
        for (include, local_module_path) in tup:
            if include in ''.join(s):
                if "LOCAL_PROPRIETARY_MODULE" not in ''.join(s):
                    if local_module_path in ''.join(s):
                        nb_err = nb_err+1
                        if not light:
                            warning_message(nb_err, f, warning_message1, s)
                            print_vendor("instead of "+local_module_path+" to have module in vendor in :")
                            for l in s:
                                print l
                    else:
                        if local_module_path not in ''.join(s):
                            nb_err = nb_err+1
                            if light:
                                light_message(f, s)
                            else:
                                warning_message(nb_err, f, warning_message2, s)
                                for l in s:
                                    print l
                else:
                    if re.search(r"LOCAL_MODULE_PATH.*TARGET_OUT(?!_VENDOR).*", ''.join(s)) is not None:
                        nb_err = nb_err+1
                        if light:
                            light_message(f, s)
                        else:
                            warning_message(nb_err, f, warning_message2, s)
                            print_vendor("Remove TARGET_OUT to let Android build system detect path using LOCAL_PROPRIETARY_MODULE:=true or use TARGET_OUT_VENDOR :")
                            for l in s:
                                print l

    return nb_err, out


def get_module(section):
    try:
        found = re.search(r"LOCAL_MODULE(?!_).*(:=)(.*)", '\n'.join(section)).group(2)
    except AttributeError:
        found = None
    return found


def find_makefiles(directory):
    makefiles = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.endswith('.mk'):
                makefiles.append(root+'/'+f)
    return makefiles


def main():

    usage = "usage: %prog [options] makefile1 makefile2 ..."
    description = ("Tool to verify if Intel binaries are going to the right output path. \n \
                    If option -p is selected makefiles listed (makefile1 makefile2 ...) will be ignored.")

    parser = OptionParser(usage, description=description)

    parser.add_option("-p", "--path", dest="path",
                      help=("All makefiles will be checked in the given path"))

    parser.add_option("-l", "--light", dest="light", action='store_true',
                      help=("Messages will be limited to one line per module"))

    (options, args) = parser.parse_args()

    nb_err = 0
    nb_err_tmp = 0
    num_mk = 0

    if options.path:
        makefile = find_makefiles(options.path)
    else:
        makefile = args

    tup = [('BUILD_EXECUTABLE', 'TARGET_OUT_VENDOR_EXECUTABLES'),
           ('BUILD_PREBUILT', 'TARGET_OUT_VENDOR'),
           ('BUILD_SHARED_LIBRARY', 'TARGET_OUT_VENDOR_SHARED_LIBRARIES'),
           ('BUILD_JAVA_LIBRARY', 'TARGET_OUT_VENDOR_JAVA_LIBRARIES'),
           ('BUILD_PACKAGE', 'TARGET_OUT_VENDOR_APPS')]

    searched_output = []
    try:
        for mk in makefile:
            nb_err, searched_output = search_string(options.light, tup, mk, nb_err, searched_output)
            if nb_err is not nb_err_tmp:
                num_mk = num_mk+1
                nb_err_tmp = nb_err

        if not options.light:
            if nb_err is not 0:
                print separative_line
                print_vendor(informative_message)
                print separative_line
        else:
            print "\n"
            print informative_message_light

    except IOError:
        print 'No *.mk found in this folder'
    return 0

if __name__ == "__main__":
    exit(main())
