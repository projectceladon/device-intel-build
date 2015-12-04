#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-

# Copyright (c) 2014, Intel Corporation.
# Author: Perrot, ThomasX <thomasx.perrot@intel.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms and conditions of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.

"""
Script to create a GPT/UEFI image or to show information it contains.
"""

from sys import version_info

if version_info < (2, 7, 3):
    exit('Python version must be 2.7.3 or higher')

from logging import (debug, info, error, DEBUG, INFO, getLogger,
                     basicConfig)
from argparse import ArgumentParser
from os import remove, stat
from os.path import isfile, normcase, normpath, realpath
from struct import unpack, pack
from uuid import UUID, uuid4
from binascii import crc32
from re import compile as re_compile
from collections import namedtuple
from ConfigParser import SafeConfigParser, ParsingError, NoOptionError
from math import floor, log


class MBRInfos(object):
    """
    Named tuple of MBR information.

    Raw MBR is a little-endian struct with:
    +--------------------------------------------+
    | name         | type    | size     | format |
    +==============+=========+==========+========+
    | boot         | int     | 4        | I      |
    +--------------+---------+----------+--------+
    | OS type      | int     | 4        | I      |
    +--------------+---------+----------+--------+
    | starting LBA | uint    | 4        | I      |
    +--------------+---------+----------+--------+
    | size in LBA  | uint    | 4        | I      |
    +--------------+---------+----------+--------+
    | dummy 1      | char[]  | 430 char | 430s   |
    +--------------+---------+----------+--------+
    | dummy 2      | char[]  | 16 char  | 16s    |
    +--------------+---------+----------+--------+
    | dummy 3      | char[]  | 48 char  | 48s    |
    +--------------+---------+----------+--------+
    | sign         | char[]  | 2 char   | 2s     |
    +--------------+---------+----------+--------+
    """
    __slots__ = ('block_size', 'raw', 'boot', 'os_type', 'lba_start',
                 'lba_size', 'dummy_1', 'dummy_2', 'dummy_3', 'sign')

    _FMT = '<IIII430s16s48s2s'

    _PART_ENTRY = ('\x00\x00\x00\x00\xee\x00\x00\x00\x01\x00\x00\x00\x00\x00'
                   '\xee\x00')

    def __init__(self, block_size=512):
        self.block_size = block_size
        self.raw = ''

        # TODO use decorators and properties to subtitute by r/w access in the
        # raw attribute with pack and unpack function all these attributes
        self.boot = 0
        self.os_type = 0
        self.os_type = 0
        self.lba_start = 0
        self.lba_size = 0
        self.dummy_1 = ''
        self.dummy_2 = ''
        self.dummy_3 = ''
        self.sign = '\x55\xaa'

    def __repr__(self):
        # converts the size
        if self.lba_size > 0:
            units = ('KBytes', 'MBytes', 'GBytes')
            index = int(floor(log(self.lba_size, 1024)))
            computed_size = round(self.lba_size / (1024**index), 2)
            human_size = '{0} {1}'.format(computed_size, units[index])
        else:
            human_size = '0 Bytes'

        chs_starting = self.boot & 0x00FFFFFF
        chs_ending = self.os_type & 0x00FFFFFF

        result = 'MBR:\n'
        result = '{0}\tboot: 0x{1:02x}\n'.format(result, self.boot)
        result = '{0}\tOS type: 0x{1:02x}\n'.format(result, self.os_type)
        result = '{0}\tCHS : starting {1:d}, ending {2:d}\n' \
            .format(result, chs_starting, chs_ending)
        result = '{0}\tLBA: start {1:d}, size {2:d}\n' \
            .format(result, self.lba_start, self.lba_size)
        result = '{0}\tsize: {1}\n'.format(result, human_size)

        return result

    def read(self, img_file, offset=0):
        """
        Used to extract information of GPT raw obtains after reading an image.
        """
        # reads the image file
        img_file.seek(offset)
        self.raw = img_file.read(self.block_size)

        # unpacks the raw MBR to a named tuple
        self.boot, self.os_type, self.lba_start, self.lba_size, self.dummy_1, \
            self.dummy_2, self.dummy_3, self.sign \
            = unpack(MBRInfos._FMT, self.raw)

    def write(self, img_file, offset=0):
        """
        Used to write MBR in an image file
        """
        self.raw = pack(MBRInfos._FMT, self.boot, self.os_type,
                        self.lba_start, self.lba_size, '',
                        MBRInfos._PART_ENTRY, '', self.sign)
        img_file.seek(offset)
        img_file.write(self.raw)


class GPTHeaderInfos(object):
    """
    Named tuple of GPT/UEFI header information

    GPT/UEFI header format:
    +-----------+----------+--------------------------------------------------+
    | offset    | Length   | Contents                                         |
    +===========+==========+==================================================+
    | 0 (0x00)  | 8 bytes  | Signature ('EFI PART',                           |
    |           |          | 45h 46h 49h 20h 50h 41h 52h 54h)                 |
    +-----------+----------+--------------------------------------------------+
    | 8 (0x08)  | 4 bytes  | Revision (for GPT version 1.0 (through at least  |
    |           |          | UEFI version 2.3.1), the value is                |
    |           |          | 00h 00h 01h 00h)                                 |
    +-----------+----------+--------------------------------------------------+
    | 12 (0x0C) | 4 bytes  | Header size in little endian (in bytes,          |
    |           |          | usually 5Ch 00h 00h 00h meaning 92 bytes)        |
    +-----------+----------+--------------------------------------------------+
    | 16 (0x10) | 4 bytes  | CRC32 of header (offset +0 up to header size),   |
    |           |          | with this field zeroed during calculation        |
    +-----------+----------+--------------------------------------------------+
    | 20 (0x14) | 4 bytes  | Reserved; must be zero                           |
    +-----------+----------+--------------------------------------------------+
    | 24 (0x18) | 8 bytes  | Current LBA (location of this header copy)       |
    +-----------+----------+--------------------------------------------------+
    | 32 (0x20) | 8 bytes  | Backup LBA (location of the other header copy)   |
    +-----------+----------+--------------------------------------------------+
    | 40 (0x28) | 8 bytes  | First usable LBA for partitions (primary         |
    |           |          | partition table last LBA + 1)                    |
    +-----------+----------+--------------------------------------------------+
    | 48 (0x30) | 8 bytes  | Last usable LBA (secondary partition table first |
    |           |          | LBA - 1)                                         |
    +-----------+----------+--------------------------------------------------+
    | 56 (0x38) | 16 bytes | Disk GUID (also referred as UUID on UNIXes)      |
    +-----------+----------+--------------------------------------------------+
    | 72 (0x48) | 8 bytes  | Starting LBA of array of partition entries       |
    |           |          | (always 2 in primary copy)                       |
    +-----------+----------+--------------------------------------------------+
    | 80 (0x50) | 4 bytes  | Number of partition entries in array             |
    +-----------+----------+--------------------------------------------------+
    | 84 (0x54) | 4 bytes  | Size of a single partition entry (usually 128)   |
    +-----------+----------+--------------------------------------------------+
    | 88 (0x58) | 4 bytes  | CRC32 of partition array                         |
    +-----------+----------+--------------------------------------------------+
    | 92 (0x5C) | *        | Reserved; must be zeroes for the rest of the     |
    |           |          | block (420 bytes for a sector size of 512 bytes  |
    |           |          | but can be more with larger sector sizes)        |
    +===========+==========+==================================================+
    | LBA size  | Total    |                                                  |
    +-----------+----------+--------------------------------------------------+
    """
    __slots__ = ('raw', 'sign', 'rev', 'size', 'crc', 'lba_current',
                 'lba_backup', 'lba_first', 'lba_last', 'uuid', 'lba_start',
                 'table_length', 'entry_size', 'table_crc')

    _FMT = '<8s4sII4xQQQQ16sQIII'

    def __init__(self, img_size=2147483648, block_size=512, size=92):
        self.raw = ''

        # TODO use decorators and properties to subtitute by r/w access in the
        # raw attribute with pack and unpack function all these attributes
        self.sign = 'EFI PART'
        self.rev = '\x00\x00\x01\x00'
        self.size = size

        # sets the length and the entry size of the GPT partition table with
        # their default values
        self.table_length = 128
        self.entry_size = 128

        # calculates the size of image in block
        size_in_block = img_size / block_size

        # sets the lba backup at the value of first lba used by GPT backup
        self.lba_backup = size_in_block - 1

        # calculates the size of the partition table in block
        table_size = (self.table_length * self.entry_size) / block_size

        # sets the lba first at the first usable lba for a partition
        self.lba_first = table_size + 2

        # sets last lba at last usable lba for a partition
        self.lba_last = size_in_block - 2 - table_size

        # generates an unique disk GUID
        self.uuid = uuid4().bytes_le

        # sets lba start at the value of first lba used by GPT header
        self.lba_start = size_in_block - 1 - table_size

        self.crc = 0
        self.lba_current = 0
        self.table_crc = 0

    def __repr__(self):
        result = 'GPT Header:\n'
        result = '{0}\tsignature: {1}\n'.format(result, self.sign)
        result = '{0}\trevision: {1}\n'.format(result, self.rev)
        result = '{0}\tsize: {1} bytes\n'.format(result, self.size)
        result = '{0}\tCRC32: {1}\n'.format(result, self.crc)

        result = '{0}\tLBAs:\n'.format(result)
        result = '{0}\t\t current: {1}\n'.format(result, self.lba_current)
        result = '{0}\t\t backup: {1}\n'.format(result, self.lba_backup)
        result = '{0}\t\t first usable: {1}\n'.format(result, self.lba_first)
        result = ('{0}\t\t last usable: {1} - {2}\n'
                  .format(result, self.lba_last, self.lba_start))

        result = ('{0}Disk UUID: {1}\n'
                  .format(result, UUID(bytes_le=self.uuid)))

        result = '{0}partition entries:\n'.format(result)
        result = '{0}\tstarting LBA: {1}\n'.format(result, self.lba_start)
        result = ('{0}\tnumber of partition entries: {1}\n'
                  .format(result, self.table_length))
        result = ('{0}\tsize of a single partition: {1}\n'
                  .format(result, self.entry_size))
        result = ('{0}\tCRC32 of partition array: {1}\n'
                  .format(result, self.table_crc))

        return result

    def read(self, img_file, offset):
        """
        Used to extract information of raw gpt obtains after reading an image
        """

        # reads the image file
        img_file.seek(offset)
        self.raw = img_file.read(self.size)

        # unpacks the raw GPT header of the image file to a named tuple
        self.sign, self.rev, self.size, self.crc, self.lba_current, \
            self.lba_backup, self.lba_first, self.lba_last, self.uuid, \
            self.lba_start, self.table_length, self.entry_size, \
            self.table_crc = unpack(GPTHeaderInfos._FMT, self.raw)

    def write(self, img_file, offset, block_size):
        """
        Used to write GPT header and backup in an image file
        """
        self.raw = pack(GPTHeaderInfos._FMT, self.sign, self.rev,
                        self.size, 0, 1, self.lba_backup,
                        self.lba_first, self.lba_last, self.uuid,
                        2, self.table_length, self.entry_size, 0)

        backup_raw = pack(GPTHeaderInfos._FMT, self.sign, self.rev,
                          self.size, 0, self.lba_backup, 1,
                          self.lba_first, self.lba_last, self.uuid,
                          self.lba_start, self.table_length,
                          self.entry_size, 0)

        # writes a new GPT header
        img_file.seek(offset)
        img_file.write(self.raw)

        # writes zero on unused blocks of GPT header
        raw_stuffing = '\x00' * (block_size - len(self.raw))
        img_file.write(raw_stuffing)

        # saves the end of the GPT header
        gpt_header_end = img_file.tell()

        # writes a new GPT backup
        backup_position = self.lba_backup * block_size
        img_file.seek(backup_position)
        img_file.write(backup_raw)

        # writes zero on unused blocks of GPT backup
        img_file.write(raw_stuffing)

        # sets the read pointer at the end of GPT header wrote
        img_file.seek(gpt_header_end)


class PartTableInfos(list):
    """
    The list of partition table entries
    """
    __slots__ = ('raw')

    def __init__(self):
        super(PartTableInfos, self).__init__()
        self.raw = ''

    def __repr__(self):
        result = 'Partitions table:\n'
        for entry in self:
            if UUID(bytes_le=entry.type) == \
                    UUID('00000000-0000-0000-0000-000000000000'):
                continue
            result = '{0}{1}'.format(result, entry)

        return result

    def read(self, img_file, offset, length, entry_size):
        """
        Read the partition table from a GPT/UEFI image
        """
        img_file.seek(offset)
        self.raw = img_file.read(length * entry_size)

        # reads each entry of partition table
        for i in xrange(length):
            entry = TableEntryInfos(i, entry_size)
            entry.read(self.raw)
            self.append(entry)

    def write(self, img_file, offset, entry_size, tlb_infos, last_usable):
        """
        Used to write GPT partitions tables in an image file
        """
        # erases the partition table entries
        self = []

        # writes all new partition entries in GPT header
        current_offset = offset
        for pos, part_info in enumerate(tlb_infos):
            entry = TableEntryInfos(pos, entry_size)
            entry.write(img_file, current_offset, part_info)
            current_offset += entry_size
            self.append(entry)

        # copies all partition entries wrote from GPT header to
        # the GPT backup
        img_file.seek(offset)
        raw_entries_size = current_offset - offset
        raw_entries = img_file.read(raw_entries_size)
        img_file.seek(last_usable + 1)
        img_file.write(raw_entries)

        img_file.seek(current_offset)


class TableEntryInfos(object):
    """
    An entry of the partition table

    UUID partition entry format:

    +-----------+-----------+-------------------------------------------------+
    | Offset    | Length    | Content                                         |
    +===========+===========+=================================================+
    | 0  (0x00) | 16 bytes  | Partition type GUID                             |
    +-----------+-----------+-------------------------------------------------+
    | 16 (0x10) | 16 bytes  | Unique partition GUID                           |
    +-----------+-----------+-------------------------------------------------+
    | 32 (0x20) | 8 bytes   | First LBA (little endian)                       |
    +-----------+-----------+-------------------------------------------------+
    | 40 (0x28) | 8 bytes   | Last LBA (inclusive, usually odd)               |
    +-----------+-----------+-------------------------------------------------+
    | 48 (0x30) | 8 bytes   | Attribute flags (e.g. bit 60 denotes read-only) |
    +-----------+-----------+-------------------------------------------------+
    | 56 (0x38) | 72 bytes  | Partition name (36 UTF-16LE code units)         |
    +===========+===========+=================================================+
    | Total     | 128 bytes |                                                 |
    +-----------+-----------+-------------------------------------------------+
    """
    __slots__ = ('pos', 'size', 'raw', 'type', 'uuid', 'lba_first',
                 'lba_last', 'attr', 'name')

    _FMT = '<16s16sQQQ72s'

    def __init__(self, pos, size):
        self.pos = pos
        self.size = size
        self.raw = ''

        self.type = ''
        self.uuid = ''
        self.lba_first = 0
        self.lba_last = 0
        self.attr = 0
        self.name = ''

    def __repr__(self):
        result = 'UUID partition entry {0}\n'.format(self.pos)
        result = '\t{0}type: {1}\n'.format(result, UUID(bytes_le=self.type))
        result = '\t{0}UUID: {1}\n'.format(result, UUID(bytes_le=self.uuid))
        result = '\t{0}lfirst LBA: {1}\n'.format(result, self.lba_first)
        result = '\t{0}last LBA: {1}\n'.format(result, self.lba_last)
        result = '\t{0}attribute flags: 0x{1:08x}\n'.format(result, self.attr)
        result = '\t{0}name: {1}\n'.format(result,
                                           self.name.decode('utf-16le'))
        result = '\t{0}size: {1}\n'.format(result,
                                           self.lba_last + 1 - self.lba_first)

        return result

    def read(self, raw_table):
        """
        Read a partition table entry from a GPT/UEFI image
        """
        # computes the start and the end of the entry in the partition table
        raw_entry_start = self.pos * self.size
        raw_entry_end = (self.pos + 1) * self.size
        self.raw = raw_table[raw_entry_start:raw_entry_end]

        # unpacks the raw partition table entry read to a named tuple
        self.type, self.uuid, self.lba_first, self.lba_last, self.attr, \
            self.name = unpack(TableEntryInfos._FMT, self.raw)

    def write(self, img_file, offset, entry_info):
        """
        Use to write a partition table entries in an image file
        """
        types = {
            'Unused': '00000000-0000-0000-0000-000000000000',
            'esp': 'C12A7328-F81F-11D2-BA4B-00A0C93EC93B',
            'fat': '024DEE41-33E7-11D3-9D69-0008C781F39F',
            'boot': '0fc63daf-8483-4772-8e79-3d69d8477de4',
            'recovery': '0fc63daf-8483-4772-8e79-3d69d8477de4',
            'misc': '0fc63daf-8483-4772-8e79-3d69d8477de4',
            'metadata': '5808C8AA-7E8F-42E0-85D2-E1E90434CFB3',
            'linux': {'android_system': '0fc63daf-8483-4772-8e79-3d69d8477de4',
                      'android_cache': '0fc63daf-8483-4772-8e79-3d69d8477de4',
                      'android_data': '0fc63daf-8483-4772-8e79-3d69d8477de4',
                      'android_persistent': ('ebc597d0-2053-4b15-8b64-'
                                             'e0aac75f4db1'),
                      'android_factory': ('0fc63daf-8483-4772-8e79-'
                                          '3d69d8477de4'),
                      'android_config': ('0fc63daf-8483-4772-8e79-'
                                         '3d69d8477de4')
                      }
            }

        # checks if the partition type used is available
        if entry_info.type in types:
            if isinstance(types[entry_info.type], dict):
                tuuid = UUID(types[entry_info.type][entry_info.label]).bytes_le
            else:
                tuuid = UUID(types[entry_info.type]).bytes_le
        else:
            error('Unknown partition type: {0} {1}'
                  .format(entry_info.label, entry_info.type))
            exit(-1)

        # sets the partition uuid
        puuid = UUID(entry_info.uuid).bytes_le
        last = int(entry_info.size) + int(entry_info.begin) - 1

        self.raw = pack(TableEntryInfos._FMT, tuuid, puuid,
                        int(entry_info.begin), last, 0,
                        entry_info.label.encode('utf-16le'))

        img_file.seek(offset)
        img_file.write(self.raw)


TLB_INFO = namedtuple('TLB_INFO', ('begin', 'size', 'type', 'uuid', 'label'))


class TLBInfos(list):
    """
    TLB information extracted from the TLB partition file
    """
    __slots__ = ('path', 'format')

    def __init__(self, path):
        super(TLBInfos, self).__init__()
        self.path = path
        self._set_format()

    def __repr__(self):
        result = ''

        for item in self:
            line = ('add -b {0} -s {1} -t {2} -u {3} -l {4}'
                    '\n').format(item.begin, item.size, item.type, item.uuid,
                                 item.label)
            result = '{0}{1}'.format(result, line)

        return result

    def _set_format(self):
        """
        Identify the format of the TLB partition file
        """
        self.format = 'ini'

        with open(self.path, 'r') as tlb_file:
            for line in tlb_file:
                # determines the type of partition table file
                # If file contains "partition_table=gpt" pattern then
                # it's a JSON TLB partition file,
                # else it's probably an INI TLB partition file.
                # Parser will then check if the file is correct.
                tlb_file_type_found = line.find("partition_table=gpt")

                if tlb_file_type_found != -1:
                    self.format = 'tbl'
                    break

        debug('Partition table format: {0}'.format(self.format))

    def _read_json(self, block_size):
        """
        Used to read a JSON TLB partition file
        """
        with open(self.path, 'r') as tlb_file:
            re_parser = re_compile(r'^add\s-b\s(?P<begin>\w+)\s-s\s'
                                   '(?P<size>[\w$()-]+)\s-t\s'
                                   '(?P<type>\w+)\s-u\s'
                                   '(?P<uuid>[\w-]+)\s'
                                   '-l\s(?P<label>\w+)'
                                   )
            # reads the JSON TLB file to instantiate a the TLBInfos
            for line in tlb_file:
                debug('TLB reading line: {0}'.format(line))
                parsed_line = re_parser.match(line)

                if parsed_line:
                    debug('TLB parsed line: {0}'.format(line))
                    debug('\t begin: {0}'
                          .format(parsed_line.group('begin')))
                    debug('\t size: {0}'.format(parsed_line.group('size')))
                    debug('\t type: {0}'.format(parsed_line.group('type')))
                    debug('\t uuid: {0}'.format(parsed_line.group('uuid')))
                    debug('\t label: {0}'
                          .format(parsed_line.group('label')))

                    self.append(TLB_INFO(*parsed_line.groups()))

                else:
                    debug('TLB not parsed line: {0}'.format(line))

    def _preparse_partitions(self, cfg):
        """
        Taken from gpt_ini2bin.py
        """
        with open(self.path, 'r') as f:
            data = f.read()

            partitions = cfg.get('base', 'partitions').split()

            for l in data.split('\n'):
                words = l.split()
                if len(words) > 2:
                    if words[0] == 'partitions' and words[1] == '+=':
                        partitions += words[2:]

        return partitions

    def _read_ini(self, block_size):
        """
        Used to read a INI TLB partition file
        """
        # sets a parser to read the INI TLB partition file
        cfg = SafeConfigParser()
        try:
            cfg.read(self.path)

        except ParsingError:
            error('Invalid TLB partition file: {0}'.format(self.path))
            exit(-1)

        # gpt.ini is not a "standard" ini file because keys are not uniques
        partitionList = self._preparse_partitions(cfg)

        # sets the start lba value which the read value or uses the default
        # value
        try:
            start_lba_prev = cfg.getint('base', 'start_lba')
            debug('The start_lab value read in the TLB partition file')

        except NoOptionError:
            start_lba_prev = 2048
            info('The start_lab value is undefined in the TLB partition file,'
                 ' the default value is used: {0}'.format(start_lba_prev))

        # contructs the TLB info
        for part in partitionList:
            begin = start_lba_prev
            partname = 'partition.{0}'.format(part)
            readlen = cfg.getint(partname, 'len')

            if readlen > 0:
                size = (readlen * 1024 * 1024) / block_size
                start_lba_prev = begin + size
            else:
                size = readlen

            ptype = cfg.get(partname, 'type')
            uuid = cfg.get(partname, 'guid')
            label = cfg.get(partname, 'label')
            self.append(TLB_INFO(begin, size, ptype, uuid, label))

    def read(self, block_size):
        """
        Read a TLB file
        """
        # reads the JSON TLB partition file
        if self.format == 'tbl':
            self._read_json(block_size)

        # reads the INI TLB partition file
        else:
            self._read_ini(block_size)

    def _recompute_partition_begin(self):
        """
        Ensure that partitions do not overlap
        """
        new_begin = -1
        for pos, entry in enumerate(self):
            if new_begin == -1:
                new_begin = self[pos].begin + self[pos].size
                continue
            self[pos] = self[pos]._replace(begin=new_begin)
            new_begin += self[pos].size

    def compute_last_size_entry(self, img_size, block_size, entry_size,
                                table_length):
        """
        Compute the size of the last TLB entry
        """
        last = -1
        # reserve the size for primary and secondary gpt
        MB = 1024 * 1024
        remaining_size = (img_size - MB) / block_size - 2048
        for pos, entry in enumerate(self):
            debug('Entry size: {0}'.format(entry.size))
            if entry.size < 0:
                if (last == -1):
                    last = pos
                    continue
                else:
                    error('Only one partition of size -1 allowed')
                    exit(-1)
            remaining_size -= entry.size

        # if all entries size are already defined
        if last == -1:
            debug('All entry sizes are already defined.')
            return

        if remaining_size < 0:
            error('The image size is too small regarding partition mapping.')
            missing = -remaining_size * block_size
            error('Missing at least: {0} Bytes.'.format(missing))
            exit(-1)

        # Update the size of the partition with -1 size and recompute
        # the start of each partitions after it
        self[last] = self[last]._replace(size=remaining_size)
        self._recompute_partition_begin()


class GPTImage(object):
    """
    GPT/UEFI image.
    """
    __slots__ = ('path', 'size', 'block_size', 'mbr',
                 'gpt_header', 'table')

    ANDROID_PARTITIONS = [
        'bootloader',
        'bootloader2',
        'boot',
        'recovery',
        'misc',
        'metadata',
        'system',
        'cache',
        'data',
        'persistent',
        'factory',
        'config',
        ]

    def __init__(self, path, size='5G', block_size=512, gpt_header_size=92):

        self.path = path
        self.size = GPTImage.convert_size_to_bytes(size)
        self.block_size = block_size

        self.mbr = MBRInfos(self.block_size)
        self.gpt_header = GPTHeaderInfos(self.size, block_size,
                                         gpt_header_size)
        self.table = PartTableInfos()

    def __repr__(self):

        result = 'Read EFI information from {0}.\n'.format(self.path)
        result = '{0}{1}'.format(result, self.mbr)
        result = '{0}{1}'.format(result, self.gpt_header)
        result = '{0}{1}'.format(result, self.table)

        return result

    @classmethod
    def convert_size_to_bytes(cls, str_size):
        """
        Checks and converts the image size to Bytes.
        """
        units = ('B', 'K', 'M', 'G')

        unit = str_size[-1:].upper()

        # the image size is invalid
        if unit not in units:
            error('The size of GPT/UEFI image use an invalid unit: {0}'
                  .format(str_size))
            exit(-1)

        try:
            # convert string size to an integer
            value = int(str_size[:-1])
        except ValueError:
            error('The size of GPT/UEFI image is invalid: {0}'
                  .format(str_size))
            exit(-1)

        # the value is negative
        if value < 0:
            error('The size of GPT/UEFI image is a negative value: {0}'
                  .format(str_size))
            exit(-1)

        # the value is a Bytes
        if unit == units[0]:
            return int(str_size[:-1])

        index = units.index(unit)
        return value * 1024**index

    def read(self):
        """
        Read information from a GPT/UEFI image
        """
        # opens and reads the image file
        with open(self.path, 'rb') as img_file:

            # reads the MBR of the image file
            debug('Reading MBR from {0}'.format(self.path))
            self.mbr.read(img_file)

            # reads the GPT header of the image file
            debug('Reading GPT header from {0}'.format(self.path))
            offset = self.block_size
            self.gpt_header.read(img_file, offset)

            # reads the partition table of the image file
            debug('Reading partition table from {0}'.format(self.path))
            offset = self.block_size * self.gpt_header.lba_start
            self.table.read(img_file, offset, self.gpt_header.table_length,
                            self.gpt_header.entry_size)

    def _write_crc(self, img_file):
        """
        Calculate and write CRC32 of GPT partition table, header and backup
        """
        # reads partition tables
        img_file.seek(2 * self.block_size)
        raw_table = img_file.read(self.gpt_header.table_length *
                                  self.gpt_header.entry_size)
        img_file.seek((self.gpt_header.lba_backup - 32) * self.block_size)
        raw_backup_table = img_file.read(self.gpt_header.table_length *
                                         self.gpt_header.entry_size)

        # computes CRC 32 partition tables
        table_crc = crc32(raw_table) & 0xffffffff
        backup_table_crc = crc32(raw_backup_table) & 0xffffffff

        # creates raw with the calculated CRC32 of partition tables
        raw_table_crc = pack('<I', table_crc)
        raw_backup_table_crc = pack('<I', backup_table_crc)

        # writes the calculated CRC 32 of partition table in GPT header
        img_file.seek(self.block_size + 88)
        img_file.write(raw_table_crc)

        # writes the calculated CRC 32 of partition table in GPT backup
        img_file.seek(self.size - self.block_size + 88)
        img_file.write(raw_backup_table_crc)

        # reads the GPT header
        img_file.seek(self.block_size)
        raw_header = img_file.read(self.gpt_header.size)

        # calcultates the CRC 32 of GPT header
        header_crc = crc32(raw_header) & 0xffffffff

        # creates a raw with the calculated CRC32 of GPT header
        raw_header_crc = pack('<I', header_crc)

        # writes calculated CRC 32 of GPT header
        img_file.seek(self.block_size + 16)
        img_file.write(raw_header_crc)

        # reads the GPT backup
        img_file.seek(self.size - self.block_size)
        raw_backup = img_file.read(self.gpt_header.size)

        # calcultates CRC 32 of GPT backup
        backup_crc = crc32(raw_backup) & 0xffffffff

        # creates a raw with the calculated CRC32 of GPT backup
        raw_backup_crc = pack('<I', backup_crc)

        # writes the calculated CRC 32 of GPT backup
        img_file.seek(self.size - self.block_size + 16)
        img_file.write(raw_backup_crc)

    def _write_partitions(self, img_file, tlb_infos, binaries_path):
        """
        Used to write partitions of image with binary files given. Call by
        write method
        """
        for tlb_part in tlb_infos:
            # removes the prefix "android_"
            truncated_label = tlb_part.label[8:]

            # gives the path of binary used to write the partition
            bin_path = binaries_path[truncated_label]

            # computes the partition offset
            offset = int(tlb_part.begin) * self.block_size

            # no binary file used to build the partition
            if bin_path == 'none':
                line = '\0x00'
                img_file.seek(offset)
                img_file.write(line)
                bin_size = 0
                continue

            # checks if partition size is greather or equal to the binary file
            bin_size_in_bytes = stat(bin_path).st_size
            part_size_in_bytes = tlb_part.size * self.block_size
            bin_size = bin_size_in_bytes / self.block_size
            if tlb_part.size < bin_size:
                error('Size of binary file {0} ({1} Bytes) is greather than '
                      '{2} partition size ({3} Bytes)'.format(bin_path,
                                                              bin_size_in_bytes,
                                                              tlb_part.label,
                                                              part_size_in_bytes))
                exit(-1)

            # opens and reads the binary file to write the partition
            with open(bin_path, 'rb') as bin_file:
                img_file.seek(offset)
                # Doesn't work if image size exceed the largest integer on that
                # machine, image size is intepreted as a negative size by
                # Python interpeter
                # for line in bin_file:
                #     img_file.write(line)
                while True:
                    data = bin_file.read(8192)
                    if not data:
                        break
                    img_file.write(data)

    def write(self, tlb_infos, binaries_path):
        """
        Used to write a new GPT/UEFI image with values read in TLB file and the
        binaries
        """
        with open(self.path, 'wb+') as img_file:
            info('Launch the write of GPT/UEFI image: {0}'.format(self.path))

            # fill output image header with 0x00: MBR size + GPT header size +
            # (partition table length * entry size)
            zero = '\x00' * (2 * self.block_size +
                             self.gpt_header.table_length *
                             self.gpt_header.entry_size)
            img_file.seek(0)
            img_file.write(zero)

            info('Writing the MBR of the GPT/UEFI image: {0}'
                 .format(self.path))
            offset = 0
            self.mbr.write(img_file, offset)

            info('Writing the GPT Header of the GPT/UEFI image: {0}'
                 .format(self.path))
            offset = self.block_size
            self.gpt_header.write(img_file, offset, self.block_size)

            info('Writing the primary partition table of the GPT/UEFI'
                 ' image: {0}'
                 .format(self.path))
            offset = 2 * self.block_size
            self.table.write(img_file, offset, self.gpt_header.entry_size,
                             tlb_infos, self.gpt_header.lba_last)

            info('Writing the secondary partition table of the'
                 ' GPT/UEFI image: {0}'
                 .format(self.path))
            offset = (self.gpt_header.lba_backup - 32) * self.block_size
            self.table.write(img_file, offset, self.gpt_header.entry_size,
                             tlb_infos, self.gpt_header.lba_last)

            info('Writing partitions of the GPT/UEFI image {0}'
                 .format(self.path))
            self._write_partitions(img_file, tlb_infos, binaries_path)

            info('Calculating the GPT/UEFI image CRCs and write them')
            self._write_crc(img_file)

            info('GPT/UEFI Image {0} created successfully !!!'
                 .format(self.path))


def usage():
    """
    Used to make main args parser and helper
    """

    # definition of parameters parser
    cmdparser = ArgumentParser(description=__doc__)

    # command line option used to specify the GPT/UEFI image filename
    cmdparser.add_argument('FILE', type=str, help=('The path of GPT/UEFI '
                                                   'image.'))

    cmds_group = cmdparser.add_mutually_exclusive_group()

    # command line option used to show information read in a GPT/UEFI image
    cmds_group.add_argument('--show', action='store_true',
                            help='Command to show GPT/UEFI image information.')

    # command line option used to create a GPT/UEFI image
    cmds_group.add_argument('--create', action='store_true',
                            help='Command to create a new GPT/UEFI image.')
    create_group = cmdparser.add_argument_group('create')

    # command line option to print debug information
    cmdparser.add_argument('-g', '--debug', action='store_true',
                           help='Verbose debug information.')

    # commande line option used to specify the path of TBL file
    create_group.add_argument('--table', action='store',
                              help='The path of the partition table file.')

    # command line option used to specify a new block size value
    create_group.add_argument('--block', action='store', type=int,
                              default=512, help=('The size of a block in Bytes'
                                                 ' [default=512].'))

    # command line option used to specify the size of image wrote
    create_group.add_argument('--size', action='store', type=str, default='5G',
                              help=('the size of the GPT/UEFI image in Bytes '
                                    '[default: 5G]'))

    # command line option used to specify binary filename used to wrote
    # partitions of new image file
    for item in GPTImage.ANDROID_PARTITIONS:
        create_group.add_argument('--{0}'.format(item), action='store',
                                  type=str, default='none',
                                  help=('the path of the binary file used to '
                                        'create the partition {0} or none'
                                        .format(item)))

    return cmdparser


def main():
    """
    main function used to create or to show GPT/UEFI image information
    """
    # catches the command line parameters
    cmdargs = usage().parse_args()

    # sets the logger
    logger = getLogger()
    basicConfig(format=' %(levelname)s %(message)s')

    # sets the level of logger
    if cmdargs.debug:
        logger.setLevel(DEBUG)
    else:
        logger.setLevel(INFO)

    # inits the block size value, the default value used is 512 Bytes
    block_size = cmdargs.block

    # checks if the block size value is valid
    if block_size <= 0:
        error('Invalid block size value: {0} Octets'.format(block_size))
        exit(-1)

    # normalizes the path of GPT/UEFI image
    img_path = realpath(normpath(normcase(cmdargs.FILE)))

    # checks the image size value
    img_size = cmdargs.size

    # create an instance of GPTImage with the GPT/UEFI image path and the block
    # size value
    gpt_img = GPTImage(img_path, img_size, block_size)

    # processes the command to create and to write GPT/UEFI image through a TBL
    # partition file and binary filenames
    if cmdargs.create:

        info('The GPT/UEFI image size: {0}'.format(img_size))

        # normalizes and check if the path of TBL partition file is valid
        tlb_path = realpath(normpath(normcase(cmdargs.table)))
        if not isfile(tlb_path):
            error('The path of partition table is invalid: {0}'
                  .format(tlb_path))
            exit(-1)

        # reads the TLB partition file
        tlb_infos = TLBInfos(tlb_path)
        info('Reading the partition file {0} of type {1}'
             .format(tlb_infos.path, tlb_infos.format))
        tlb_infos.read(gpt_img.block_size)

        # computes the size of last entry, its size may be undefined
        tlb_infos.compute_last_size_entry(gpt_img.size,
                                          gpt_img.block_size,
                                          gpt_img.gpt_header.entry_size,
                                          gpt_img.gpt_header.table_length
                                          )

        # checks if the TLB partition file read contains valid information
        if not tlb_infos:
            error('The partition table contains invalid value(s): {0}'
                  .format(tlb_path))
            exit(-1)

        # prints TLB information read
        debug(tlb_infos)

        # creates the list of necessary binaries used to wrote GPT/UEFI image
        binaries_path = {}
        for label in GPTImage.ANDROID_PARTITIONS:

            # if the binary file is undefined
            bin_path = getattr(cmdargs, label)
            if bin_path == 'none':
                debug('Partition {0} doesn\'t use a binary file'.format(label))
                binaries_path[label] = bin_path
                continue

            # check if binary file exist
            norm_bin_path = realpath(normpath(normcase(bin_path)))
            if not isfile(norm_bin_path):
                error('The binary used to create the partition "{0}" is '
                      'invalid: {1}'.format(label, norm_bin_path))
                exit(-1)

            debug('Partition {0} uses this binary file: {1}'
                  .format(label, norm_bin_path))
            binaries_path[label] = norm_bin_path

        # removes the GTP image, if it already exists
        if isfile(img_path):
            info('Deleting the GPT/UEFI image previous created: {0}'
                 .format(img_path))
            remove(img_path)

        # calls function to write new GPT/UEFI image
        gpt_img.write(tlb_infos, binaries_path)

    # checks if the GPT/UEFI image exists
    if not isfile(img_path):
        error('GPT/UEFI image not found: {0}'.format(img_path))
        exit(-1)

    # reads the GPT/UEFI image to check it's valid, it uses CRC32
    gpt_img.read()

    # processes the command show, to print information of the GPT/UEFI image
    if cmdargs.show:
        print(gpt_img)

    exit(0)

if __name__ == '__main__':
        main()
