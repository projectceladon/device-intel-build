from blobstore import *

def test1():
    db = BlobStore()
    db.create('db.txt', 1024)
    for i in xrange(1, 1024):
        str = 'This is my blob:' + `i`
        blobKey = 'key' + `i`
        db.putBlob(str, len(str), blobKey, BLOBTYPES.BlobTypeDtb)
        db.putBlob(str, len(str), blobKey, BLOBTYPES.BlobTypeOemVars)
    db.close()
    db = BlobStore()
    db.load('db.txt')
    # db.printInfo()
    for i in xrange(1, 1024):
        blobKey = 'key' + `i`
        blob = db.getBlob(blobKey, BLOBTYPES.BlobTypeDtb)
        print blob
        db.getBlob(blobKey, BLOBTYPES.BlobTypeOemVars)
        print blob
    db.close()

def main():
    test1()

if __name__ == '__main__':
    main()
