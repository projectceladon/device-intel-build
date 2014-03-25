#!/usr/bin/env python

import sys
import os
import stat
import getopt

def usage():
    print "Usage: updateblob.py -o <output file> <list of input EFI binaries>"

def write_blobs(files, outfilename):
    ofd = open(outfilename, "wb")
    ofd.write(str(len(files))+'\n')

    for fil in files:
        sz = os.path.getsize(fil)
        # write file header
        ofd.write(os.path.split(fil)[1] + "," + str(int(sz)) + "\n")
        ifd = open(fil ,"rb")
        ofd.write(ifd.read())
        ifd.close()
    ofd.close()

if __name__ == '__main__':
    files = []
    outfile = None

    try:
        opts, files = getopt.getopt(sys.argv[1:], "o:h", ["output=", "help"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-o", "--output"):
            outfile = a

    if not files or not outfile:
        usage()
        sys.exit(1)

    write_blobs(files, outfile)

