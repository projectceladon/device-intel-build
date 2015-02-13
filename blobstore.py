import sys
import os
import struct
from ctypes import *
from collections import namedtuple

BLOB_KEY_LENGTH = 64
_BLOBTYPES = namedtuple('BlobTypes', 'BlobTypeDtb BlobTypeOemVars')
BLOBTYPES = _BLOBTYPES(0, 1)

def ValidBlobType(blobType):
    if(blobType >= BLOBTYPES.BlobTypeDtb and
         blobType <= BLOBTYPES.BlobTypeOemVars):
        return True
    else:
        return False

class SuperBlock:
    _structFormat = struct.Struct('8s I I I I I')
    _SuperBlockMagic = '####FFFF'

    def __init__(self, numberOfBlocks=0, blockSize=0):
        self._magic = '####FFFF'
        self._version = 1
        self._numberOfBlocks = numberOfBlocks
        self._blockSize = blockSize
        self._blobsLocation = (self._structFormat.size +
                               1 + (numberOfBlocks * blockSize))
        self._blobsEndLocation = self._blobsLocation

    def getOnDiskSize(self):
        return self._structFormat.size

    def getNumberOfBlocks(self):
        return self._numberOfBlocks

    def getBlobsEndLocation(self):
        return self._blobsEndLocation

    def expandBlobsEndLocation(self, size):
        self._blobsEndLocation += size

    def validateMagic(self):
        if(self._magic != self._SuperBlockMagic):
            raise Exception('SuperBlock Magic invalid')

    def read(self, _file):
        if (_file is None):
            raise Exception('fileHandle is invalid')

        _file.seek(0, 0)
        data = _file.read(self.getOnDiskSize())
        (self._magic,
         self._version,
         self._numberOfBlocks,
         self._blockSize,
         self._blobsLocation,
         self._blobsEndLocation) = self._structFormat.unpack(data)

        self.validateMagic()

    def write(self, _file):
        if(_file is None):
            raise Exception('filehandle is invalid')
        _file.seek(0, 0)

        self.validateMagic()
        packed_data = self._structFormat.pack(self._magic,
                                              self._version,
                                              self._numberOfBlocks,
                                              self._blockSize,
                                              self._blobsLocation,
                                              self._blobsEndLocation)
        _file.write(packed_data)
        _file.flush()

    def printInfo(self):
        print 'SuperBlock:'
        print '_magic: %s' % self._magic
        print '_version: %d' % self._version
        print '_numberOfBlocks: %d' % self._numberOfBlocks
        print '_blockSize: %d' % self._blockSize
        print '_blobsLocation: %d' % self._blobsLocation
        print '_blobsEndLocation: %d' % self._blobsEndLocation
        print '..............'


class MetaBlob:
    _structFormat = struct.Struct('I I I')
    _onDiskSize = _structFormat.size

    def __init__(self, blobType=-1, blobLocation=0, blobSize=0):
        self._blobType = blobType
        self._blobLocation = blobLocation
        self._blobSize = blobSize
        self._used = 'false'

    def onDiskSize(self):
        return self._onDiskSize

    def setBlob(self, blobLocation=0, blobSize=0):
        self._blobLocation = blobLocation
        self._blobSize = blobSize
        self._used = 'true' if (
            self._blobLocation > 0 and self._blobSize > 0) else 'false'

    def packInto(self, buf, offset):
        if (buf == None):
            raise Exception('invalid buf')

        self._structFormat.pack_into(
            buf, offset, self._blobType, self._blobLocation, self._blobSize)
        return

    def unpackFrom(self, buf, offset):
        if (buf == None):
            raise Exception('invalid buf')
        (self._blobType,
         self._blobLocation,
         self._blobSize) = self._structFormat.unpack_from(buf, offset)
        self._used = 'true' if (
            self._blobLocation > 0 and self._blobSize > 0) else 'false'

    def printInfo(self):
        print 'MetaBlob:'
        print '_blobType %s' % self._blobType
        print '_blobLocation %d' % self._blobLocation
        print '_blobSize %d' % self._blobSize
        print '......................'
        return


class MetaBlock:
    _structFormat = struct.Struct('8s I I 64s')
    _MetaBlockMagic = 'FFFF####'
    _metaBlobsTypeUnknown = 0
    _onDiskSize = _structFormat.size + (MetaBlob._onDiskSize * len(BLOBTYPES))
    _metaBlobsSize = MetaBlob._onDiskSize * len(BLOBTYPES)

    def __init__(self, blockNumber=0):
        self._magic = 'FFFF####'
        self._blockId = 0
        self._blockNumber = blockNumber
        self._blobKey = chr(0) * BLOB_KEY_LENGTH
        self._metaBlobs = [None]*len(BLOBTYPES)
        self._used = 'false'
        for blobType in BLOBTYPES:
            blob = MetaBlob(blobType, 0, 0)
            self._metaBlobs[blobType] = blob

    def getBlobInfo(self, blobType):
        if(not ValidBlobType(blobType)):
            return (-1,0)
        return (self._metaBlobs[blobType]._blobLocation,
                self._metaBlobs[blobType]._blobSize)

    def setBlob(self, blobKey, blobType, blobLocation, blobSize):
        if(not ValidBlobType(blobType)):
            return
        self._blobKey = blobKey
        if(blobLocation > 0 and blobSize > 0):
            self._used = 'true'
        self._metaBlobs[blobType].setBlob(blobLocation, blobSize)

    def validateMagic(self):
        if(self._magic != self._MetaBlockMagic):
            raise Exception('MataBlock magic Invalid')

    def packBlobs(self):
        offset = 0
        buf = create_string_buffer(MetaBlock._metaBlobsSize)
        for blob in self._metaBlobs:
            blob.packInto(buf, offset)
            offset += blob.onDiskSize()
        return buf

    def unpackBlobs(self, packedBuf):
        if(packedBuf == None):
            raise Exception('MataBlock magic Invalid')
        offset = 0
        for blob in self._metaBlobs:
            blob.unpackFrom(packedBuf, offset)
            offset += blob.onDiskSize()
        return

    def read(self, _file, blockLocation):
        if (_file == None):
            raise Exception('filehandle is invalid')
        _file.seek(blockLocation, 0)
        data = _file.read(self._structFormat.size)

        (self._magic,
         self._blockId,
         self._blockNumber,
         self._blobKey) = self._structFormat.unpack(data)

        self.validateMagic()

        blobsBuf = _file.read(MetaBlock._metaBlobsSize)
        self.unpackBlobs(blobsBuf)
        for blob in self._metaBlobs:
            if(blob._used == 'true'):
                self._used = 'true'
                break

        return

    def write(self, _file, blockLocation):
        if(_file == None):
            raise Exception('fileHandle is invalid')
        _file.seek(blockLocation, 0)

        self.validateMagic()

        packed_data = self._structFormat.pack(self._magic,
                                              self._blockId,
                                              self._blockNumber,
                                              self._blobKey)
        _file.write(packed_data)
        packedBlobs = self.packBlobs()
        _file.write(packedBlobs)
        _file.flush()
        return

    def printInfo(self):
        print 'metaBlock:'
        print '_magic: %s' % self._magic
        print '_blockId: %d' % self._blockId
        print '_blockNumber: %d' % self._blockNumber
        print '_blobKey: %s' % self._blobKey
        print 'Blobs:'
        for blob in self._metaBlobs:
            blob.printInfo()
        print '_used: %s' % self._used
        print '...............'


class BlobStore:

    def __init__(self):
        self._file = None
        self._superBlock = None
        self._blocksList = {}
        self._freeBlocksList = []

    def calcBlockLocation(self, blockNumber):
        return self._superBlock.getOnDiskSize() + 1 \
            + ((blockNumber - 1) * self._superBlock._blockSize)

    def load(self, path):
        print 'Loading BlobStore...'
        if os.path.exists(path):
            self._file = open(path, 'rb+')
        else:
            print 'failure to load db'
            raise Exception('failed to load db')

        # read superblock
        self._superBlock = SuperBlock()
        self._superBlock.read(self._file)

        # read all metablocks
        for blockNumber in range(1, self._superBlock._numberOfBlocks + 1):
            block = MetaBlock(blockNumber)
            blockLocation = self.calcBlockLocation(blockNumber)
            block.read(self._file, blockLocation)
            if(block._used == 'false'):
                self._freeBlocksList.append(block)
            else:
                self._blocksList.update({block._blobKey:block})

    def create(self, path, size):
        # Create the file
        print 'Creating BlobStore...'
        self._file = open(path, 'wb+')
        if (self._file is None):
            raise Exception('failed to create database')

        # create superBlock
        print 'creating superBlock...'
        self._superBlock = SuperBlock(size, MetaBlock._onDiskSize)
        self._superBlock.write(self._file)

        # write metablocks
        print 'creating metablocks...'
        for blockNumber in range(1, size + 1):
            metablock = MetaBlock(blockNumber)
            blockLocation = self.calcBlockLocation(blockNumber)
            metablock.write(self._file, blockLocation)
            self._freeBlocksList.append(metablock)

    def getFreeBlock(self):
        return self._freeBlocksList.pop(0)

    def addToBlocksList(self, block):
        block._used = 'true'
        self._blocksList.update({block._blobKey:block})

    def getBlob(self, blobKey, blobType):
        if not ValidBlobType(blobType):
            print 'Invalid blobType'
            return None

        blobKeyFixed = blobKey.ljust(BLOB_KEY_LENGTH, '\0')

        matchedBlock = self._blocksList.get(blobKeyFixed)
        if(matchedBlock is None):
            print 'No Blob found with given key %s' % blobKey
            return None

        blobLocation, blobSize = matchedBlock.getBlobInfo(blobType)
        if not (blobLocation > 0 and blobSize > 0):
            raise Exception('Invalid blobLocation or Size')

        self._file.seek(blobLocation, 0)
        blob = self._file.read(blobSize)
        if (blob is None):
            print 'Unable to retrieve the blob'
        return blob

    def putBlob(self, blob, blobSize, blobKey, blobType):

        blobKeyFixed = blobKey.ljust(BLOB_KEY_LENGTH, '\0')
        if not ValidBlobType(blobType):
            print 'Invalid blob Type'
            return False

        if blobSize <= 0:
            print 'Invalid blobSize'
            return False

        matchedBlock = self._blocksList.get(blobKeyFixed)
        if matchedBlock is None:
            block = self.getFreeBlock()
        else:
            block = matchedBlock

        if block is None:
            print 'no more storage available'
            raise Exception('No more space')

        blobLocation = self._superBlock.getBlobsEndLocation()
        block.setBlob(blobKeyFixed, blobType, blobLocation, blobSize)
        self._superBlock.expandBlobsEndLocation(blobSize)

        # write blob to file first
        self._file.seek(blobLocation, 0)
        self._file.write(blob)
        self._file.flush()

        # persist meta block
        self.addToBlocksList(block)
        blockLocation = self.calcBlockLocation(block._blockNumber)
        block.write(self._file, blockLocation)
        block.printInfo()
        self._superBlock.write(self._file)
        return True

    def close(self):
        if (self._file is not None):
            self._file.close()

    def printInfo(self):
        self._superBlock.printInfo()
        print '------used blocked-----'
        for block in self._blocksList:
            block.printInfo()
        print '-----free blocks------'
        for block in self._freeBlocksList:
            block.printInfo()
