#!/usr/bin/env python

# Copyright (c) 2015, Intel Corporation.
# Author: Leo Sartre <leox.sartre@intel.com>

import sys
import struct
import array

rsci_header = struct.Struct('< 4c I B B 6c 8c I 4c I')
rsci_fields_v1 = struct.Struct('< B B B B I')
rsci_fields_v2 = struct.Struct('< B B B B I I')

# dictionary to translate values into a human readable format
translate_dict = {'wake_source': ["WAKE_NOT_APPLICABLE",
                                  "WAKE_BATTERY_INSERTED",
                                  "WAKE_USB_CHARGER_INSERTED",
                                  "WAKE_ACDC_CHARGER_INSERTED",
                                  "WAKE_POWER_BUTTON_PRESSED",
                                  "WAKE_RTC_TIMER",
                                  "WAKE_BATTERY_REACHED_IA_THRESHOLD"],
                  'reset_source_v1': ["RESET_NOT_APPLICABLE",
                                   "RESET_OS_INITIATED",
                                   "RESET_FORCED",
                                   "RESET_FW_UPDATE",
                                   "RESET_KERNEL_WATCHDOG",
                                   "RESET_SECURITY_WATCHDOG",
                                   "RESET_SECURITY_INITIATED",
                                   "RESET_PMC_WATCHDOG",
                                   "RESET_EC_WATCHDOG",
                                   "RESET_PLATFORM_WATCHDOG"],
                  'reset_source_v2': ["RESET_NOT_APPLICABLE",
                                   "RESET_OS_INITIATED",
                                   "RESET_FORCED",
                                   "RESET_FW_UPDATE",
                                   "RESET_KERNEL_WATCHDOG",
                                   "RESERVED_5",
                                   "RESERVED_6",
                                   "RESERVED_7",
                                   "RESET_EC_WATCHDOG",
                                   "RESET_PMIC_WATCHDOG",
                                   "RESERVED_10",
                                   "RESET_SHORT_POWER_LOSS",
                                   "RESET_PLATFORM_SPECIFIC"],
                  'shutdown_source': ["SHTDWN_NOT_APPLICABLE",
                                      "SHTDWN_POWER_BUTTON_OVERRIDE",
                                      "SHTDWN_BATTERY_REMOVAL",
                                      "SHTDWN_VCRIT",
                                      "SHTDWN_THERMTRIP",
                                      "SHTDWN_PMICTEMP",
                                      "SHTDWN_SYSTEMP",
                                      "SHTDWN_BATTEMP",
                                      "SHTDWN_SYSUVP",
                                      "SHTDWN_SYSOVP",
                                      "SHTDWN_SECURITY_WATCHDOG",
                                      "SHTDWN_SECURITY_INITIATED",
                                      "SHTDWN_PMC_WATCHDOG",
                                      "SHTDWN_EC_WATCHDOG",
                                      "SHTDWN_PLATFORM_WATCHDOG"],
                  'reset_type': ["NOT_APPLICABLE",
                                 "WARM_RESET",
                                 "COLD_RESET",
                                 "RESERVED_3",
                                 "RESERVED_4",
                                 "RESERVED_5",
                                 "RESERVED_6",
                                 "GLOBAL_RESET"]
}


def translate(field, value):
    ret = "NO_TRANSLATION_AVAILABLE"
    if (field in translate_dict.keys()):
        if (value < len(translate_dict[field])):
            ret = translate_dict[field][value]
        else:
            ret = "UNKNOWN_VALUE"
    return ret


def usage():
    print "usage: {0} <RSCI_TABLE>".format(sys.argv[0])


def verify_checksum(f):
    fd = open(f, mode='rb')
    rsci_table = array.array('B', fd.read())
    fd.close()
    return sum(rsci_table) % 0x100


def print_header(header):
    print "RSCI HEADER"
    print "\tsignature        : {}".format(''.join(header[0:4]))
    print "\tlength           : {}".format(header[4])
    print "\trevision         : {}".format(header[5])
    print "\toemid            : {}".format(''.join(header[7:13]))
    print "\toem_table_id     : {}".format(''.join(header[13:21]))
    print "\toem_revision     : {}".format(header[21])
    print "\tcreator_id       : {}".format(''.join(header[22:26]))
    print "\tcreator_revision : 0x{0:x}".format(header[26])


def print_fields(fields, revision):
    print "RSCI FIELDS"
    print "\twake_source      : {0} ({1})".format(fields[0], translate('wake_source', fields[0]))
    if (revision == 2):
        print "\treset_source     : {0} ({1})".format(fields[1], translate('reset_source_v2', fields[1]))
    else:
        print "\treset_source     : {0} ({1})".format(fields[1], translate('reset_source_v1', fields[1]))
    print "\treset_type       : {0} ({1})".format(fields[2], translate('reset_type', fields[2]))
    print "\tshutdown_source  : {0} ({1})".format(fields[3], translate('shutdown_source', fields[3]))
    print "\tindicator        : {0}".format(fields[4])
    if (revision == 2):
        print "\treset extra info : 0x{0:x}".format(fields[5])


def print_table(header, fields, revision):
    print_header(header)
    print_fields(fields, revision)


def dump_binary_table(f):
    fd = open(f, mode='rb')
    header = rsci_header.unpack(fd.read(rsci_header.size))
    revision = header[5]
    if (revision == 1):
        fields = rsci_fields_v1.unpack(fd.read(rsci_fields_v1.size))
    elif (revision == 2):
        fields = rsci_fields_v2.unpack(fd.read(rsci_fields_v2.size))
    else:
        print "Error: Unknown revision {}".format(revision)
        fd.close()
        exit(-1)
    print_table(header, fields, revision)
    fd.close()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        # Before using the table, we compute the sum of fields
        # It should be equal to zero (mod 0x100), otherwise the table
        # is corrupted
        if (verify_checksum(sys.argv[1]) == 0):
            dump_binary_table(sys.argv[1])
        else:
            print "Error: Table is corrupted!"
            exit(-1)
    else:
        usage()
        exit(-1)
