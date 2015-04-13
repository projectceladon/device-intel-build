#!/usr/bin/python

from blobstore import *
import os
import sys, getopt
import json
import argparse

def main(argv):
    args = None
    configData = None
    configKeys = None
    #verify options
    try:
        rootPath = os.getenv("ANDROID_BUILD_TOP")
        if rootPath is None:
            sys.stderr.write("Error: ANDROID_BUILD_TOP not defined. Please run envsetup.sh")
            sys.exit(1)
        parser = argparse.ArgumentParser()
        parser.add_argument('--config',required=True,
                        help="blob configuration file")
        parser.add_argument('--output',required=True,
                        help="blobstore output file path")
        args = parser.parse_args()
    except argparse.ArgumentError:
        sys.stderr.write('build_blobstore.py -c <config> -o <output>')
        sys.exit(1)

    #parse config file
    try:
        in_file = open(args.config, 'r')
        configData = json.load(in_file)
        configTypes = configData.keys()
        in_file.close()
    except ValueError, e:
        sys.stderr.write('Invalid config file')
        sys.exit(2)
    except IOError:
        sys.stderr.write("Error: File does not appear to exist.")
        sys.exit(2)

    #verify keys
    supportedTypes = []
    for configType in configTypes:
        if configType == 'oemvars':
            supportedTypes.append((configType, BLOBTYPES.BlobTypeOemVars))
        if configType == 'dtb':
            supportedTypes.append((configType, BLOBTYPES.BlobTypeDtb))

    print supportedTypes
    if not len(supportedTypes) > 0:
        sys.stderr.write('config files contains no valid types')
        sys.exit(2)

    #calculate size of blob Store
    blobStoreSize = 0
    for configType, blobType in supportedTypes:
        blobStoreSize += len(configData[configType])

    #populate datastore
    try:
        db = BlobStore()
        db.create(args.output, blobStoreSize)
        for configType,blobType  in supportedTypes:
            for data in configData[configType]:
                blobPath = data["path"]
                blobKey  = data["dmi_name"]
                absBlobPath = os.path.join(rootPath, blobPath)
                file = open(absBlobPath,'r')
                blob = file.read()
                file.close()
                ret = db.putBlob(blob, len(blob), "{0}".format(blobKey), blobType)
                if not ret == True:
                    sys.stderr.write('failed to store blob')
                    sys.exit(2)
        db.close()
    except KeyError, e:
        sys.stderr.write('Invalid KeyValue')
        system.exit(2)
    except IOError:
        sys.stderr.write('Unable to read blobfile')
        sys.exit(2)

if __name__ == '__main__':
    main(sys.argv[1:])
    sys.exit(0)
