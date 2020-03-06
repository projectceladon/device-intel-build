"""
A blobstore is essentially a serialized hash table which maps board
identification values to blobs of data. This hash table is stored inside
the Android Boot Image (in the area reserved for 2ndstage bootloader)
and lets us store various board-specific information for a large set
of boards all in the same boot image. This lets us re-use the same boot image
on a variety of different boards, a goal of the IRDA program.

The original impetus for creating this data structure was to store three
kinds of board-specific data:

    1. Device-Tree Blobs (DTBs) for the SoFIA platform, which are different for
       every board.
    2. "oemvars" which are a set of board-specific EFI variables. Use of this
       is generally being deprecated in favor of putting this data in ACPI,
       but nevertheless we still use it for tuning the bootloader and camera-
       specific values
    3. "bootvars" which are inserted verbatim into the kernel command line.
       Some boards may need special command line parameters, and we also use
       this to populate androidboot.nnn variables to create the runtime
       build fingerprint for IRDA devices.

Different boards may need multiple blobs of different types, so the hash table
is indexed by both the device identification string and also the enumerated
blob type. The format is designed to allow for the introduction of new blob
types without breaking older loaders.

We can trust everything we put in the blobstore since it is part of the boot
image and hence covered by the Google Verified Boot specification.

At build time, we just need to assemble the blobstore's contents and stick it
into the boot image. At runtime, the bootloader may need to pull values out
of the blobstore, but never modify it. Retrieval of values from the blobstore
should be as lightweight as possible.

The structure of the blobstore is as follows:

+----------------------+
| Blobstore Header     |
+----------------------+
| Hash Table           |
+----------------------+
| Meta Blocks          |
+----------------------+
| Blobs Data           |
+----------------------+

1. The header contains metadata about the entire blobstore and the size of
the array-based hash table.

struct blobstore {
    char magic[8];
    unsigned int version;
    unsigned int total_size;
    unsigned int hashmap_sz;
    unsigned int hashmap[0]; /* of hashmap_sz */
} __attribute__((packed));

2. The hash table is an array of offsets, indexed by hash value modulo the
size of the array. The offset is the location of the first of a linked list
of metablocks that correspond to a particular hash value.

3. The meta blocks are an intermediate node, one for every blob that is in
the blobstore. They are structured as a linked list to handle hash collisions.
Each meta block contains the key and type for the blob, an offset to the next
item in the list (0 for the last entry), and the offset and size of the
corresponding data.

/* All of these are packed structure with little-endian values. */
struct metablock {
    char blob_key[BLOB_KEY_LENGTH];
    unsigned int blob_type;
    unsigned int next_item_offset;
    unsigned int data_offset;
    unsigned int data_size;
} __attribute__((packed));

So in order for the loader to do a lookup, given a key and blob type, it does
the following:
1) Obtain a hash value based on the key and type
2) Use the hash table array to get the offset of the first meta block
corresponding to that hash value. If there is no offset for that hash value
in the array, the item is not found.
3) Walk the list of meta blocks and compare the supplied key/type with what
is in the meta block. Return the data and size if there is a match. Otherwise
the item isn't found.

No heap allocation or additional state variables are needed to do these lookups.
"""

import sys
import os
import struct

from sys import version_info

BLOB_KEY_LENGTH = 64
MAGIC = "BLOBSTOR"
VERSION = 1

s_metablock = struct.Struct("< %ds I I I I" % BLOB_KEY_LENGTH)
s_blobstore = struct.Struct("< 8s I I I")
s_hashitem = struct.Struct("< I")

BLOB_TYPE_DTB = 0
BLOB_TYPE_OEMVARS = 1
BLOB_TYPE_BOOTVARS = 2

# We modulo this in hashing since the value is stored in an unsigned
# 32-bit type
MAXINT = 2 ** 32

def hash_blob_key(key, btype, sz):
    hash_val = 0
    for c in key:
        hash_val = (hash_val * 31 + ord(c)) % MAXINT
    hash_val = (hash_val * 31 + btype) % MAXINT
    return hash_val % sz


class MetaBlock:

    def __init__(self, key, btype, mb_offset, data_offset, data_size):
        if version_info < (3, 0, 1):
            self.key = unicode(key).encode('utf-8')
        else:
            self.key = str(key).encode('utf-8')
        self.btype = btype
        self.next_offset = 0
        self.data_offset = data_offset
        self.data_size = data_size
        self.mb_offset = mb_offset

    def __repr__(self):
        return "<%s-%d: (%d %d %d %d)>" % (self.key, self.btype, self.mb_offset,
                self.next_offset, self.data_offset, self.data_size)

class BlobStore:

    def __init__(self, path):
        self.items = {}
        self.path = path

    def add(self, key, btype, path):
        if len(key) >= BLOB_KEY_LENGTH:
            raise Exception("Key is too long");

        # follow any symlinks
        dk = (key, btype)
        if dk in self.items:
            raise Exception("Duplicate entry in the database: "+ str(dk))
        self.items[dk] = os.path.realpath(path)

    def commit(self):
        num_entries = len(self.items)

        # Seems like a reasonable heuristic for a modulo array-based table
        hash_sz = num_entries * 2 + 1

        # Offset from the beginning where metablocks are stored, after the
        # hash table array
        mb_start = s_blobstore.size + (s_hashitem.size * hash_sz)
        mb_pos = mb_start

        # Offset from the beginning where data will be stored. Every
        # entry in the table has 1 metablock associates with it
        data_start = mb_start + (s_metablock.size * num_entries)
        data_pos = data_start

        # Map hash values to a list of metablocks for that hash.
        # We'll use this to create the hash table array itself.
        # Each entry, points to a list of metablocks.
        # The offset of the first metablock is what gets put in the table,
        # with the rest connected by a linked list.
        mbs = {}

        # Order which metablocks need to be written out, a list of
        # MetaBlock objects.
        mblist = []

        # Order in which data blobs need to be written out, a list of file paths
        datalist = []

        # Map paths to offsets. Used to filter duplicates so we can efficiently
        # support many-to-one mapping
        datadict = {}

        # Compute hashes for all the items. Duplicates are filtered
        # Also determine the total size of all the blobs. The blobs need to
        # be serialized in the same order they are in datalist.
        total_dsize = 0
        for k, path in self.items.items():
            key, btype = k
            hashval = hash_blob_key(key, btype, hash_sz)
            dsize = os.stat(path).st_size

            if hashval not in mbs:
                mbs[hashval] = []

            if path not in datadict:
                mb = MetaBlock(key, btype, mb_pos, data_pos, dsize)
                total_dsize = total_dsize + dsize
                datalist.append(path)
                datadict[path] = data_pos
                data_pos = data_pos + dsize
            else:
                mb = MetaBlock(key, btype, mb_pos, datadict[path], dsize)

            mbs[hashval].append(mb)
            mblist.append(mb)

            # Update the next pointer if we had a collision
            if len(mbs[hashval]) > 1:
                prev = mbs[hashval][-2]
                prev.next_offset = mb_pos

            mb_pos = mb_pos + s_metablock.size

        assert mb_pos == data_start
        total_size = data_start + total_dsize
        assert data_pos == total_size

        # Write the superblock
        fp = open(self.path, "wb")
        fp.write(s_blobstore.pack(MAGIC, VERSION, total_size, hash_sz))

        # Write the hash table: create an empty array, populate nonzero entries,
        # serialize it
        hlist = [0 for i in range(hash_sz)]
        for index, buckets in mbs.items():
            hlist[index] = buckets[0].mb_offset

        for offset in hlist:
            fp.write(s_hashitem.pack(offset))

        # Write all the metablocks
        for mb in mblist:
            fp.write(s_metablock.pack(mb.key, mb.btype, mb.next_offset,
                     mb.data_offset, mb.data_size))

        # Finally, write all the data
        for path in datalist:
            with open(path) as dfp:
                fp.write(dfp.read())

        fp.close()

