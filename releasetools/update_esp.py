#!/usr/bin/env python

import sys
import struct
import tempfile
import subprocess
import os
import shutil
import hashlib

class RunCmd:
    '''Fork a progress to handle some task'''    
    def Run(self, args, in_arg):
        p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        if in_arg:
            in_arg += "\n"
        p.communicate(in_arg)
        return p.returncode

class HandleFile:

    def TempFileName(self, prefix, data):
        tf = tempfile.NamedTemporaryFile(prefix=prefix, delete = False)
        if data:
            tf.write(data)
        tf.close()
        return tf.name
    
    def Write(self, str, file):
        f = open(file, "wb+")
        f.write(str)
        f.close()
    
    def Read(self, file):
        f = open(file, "rb")
        data = f.read()
        f.close()
        return data
    
    def MoveFile(self, src, dst):
        shutil.move(src, dst)
    
    def CopyFile(self, src, dst):
        shutil.copy(src, dst)

class ReplaceKey(RunCmd, HandleFile):
    '''Replace the key of efi'''
    def __init__(self, efiFilePath, keyFilePath):
        efiData = self.Read(efiFilePath)
        replaceKeyData = self.ReplaceKeyMainPro(efiData, keyFilePath)
        self.repKeyEfi = efiFilePath + ".cert"
        self.Write(replaceKeyData, self.repKeyEfi)

    def __del__(self):
        os.remove(self.repKeyEfi)

    def ReplaceKeyMainPro(self, data, oemKeyFile):  
        (oemKeysOffset, oemKeysSize) = self.GetSection(data, ".oemkeys")
        oemKeyData = self.PemCertToDer(oemKeyFile)
        oemKeyData = self.ZeroPad(oemKeyData, oemKeysSize)
        data = (data[:oemKeysOffset] + oemKeyData + data[oemKeysOffset + oemKeysSize:])
        return data
    
    def GetSection(self, data, name):
        peHeaderOffset = struct.unpack_from("<I", data, 0x3c)[0]
        numSections = struct.unpack_from("<H", data, peHeaderOffset + 0x6)[0]
        optHeaderSize = struct.unpack_from("<H", data, peHeaderOffset + 0x14)[0]
        sectionTableOffset = peHeaderOffset + 0x18 + optHeaderSize
    
        for i in range(numSections):
            sectionOffset = sectionTableOffset + (i * 0x28)
            sectionTableData = struct.unpack_from("<8sIIIIIIHHI", data, sectionOffset)
    
            sectionName, sectionSize, _, _, sectionOffset, _, _, _, _, _ = sectionTableData
            if sectionName != name:
                continue
            return (sectionOffset, sectionSize)
        print("Cannot find oemkey")
        exit()

    def PemCertToDer(self, pem_cert_path):
        fname = self.TempFileName("pem_cert_to_der_cert", None)
        ret = self.Run(["openssl", "x509", "-inform", "PEM", "-outform", "DER",
                   "-in", pem_cert_path, "-out", fname], None)
        assert ret == 0, "openssl cert conversion failed"
        der = self.Read(fname)
        os.remove(fname)
        return der

    def ZeroPad(self, data, size):
        if len(data) > size:
            print("Binary is already larger than pad size")
            exit()
        return data + (b'\x00' * (size - len(data)))

class UpdateEsp(RunCmd, HandleFile):

    def __init__(self, dir, efiFile, tos, keyPairs):
        self.key1pem = "NULL"
        self.key2pem = "NULL"
        # check parameter
        if not os.path.exists(dir):
            print("Esp partition folder does not exist")
            exit()
        if not os.path.exists(efiFile):
            print("Efi file does not exist")
            exit()
        if not os.path.exists(tos):
            print("Tos.img does not exist")
            exit()
        for key in keyPairs:
            if not os.path.exists(key):
                print("The ",key,"does not exist")
                exit() 

        self.dir = dir
        self.efiFile = efiFile
        self.key1 = keyPairs[0]
        self.key1cert = keyPairs[1]
        self.key2 = keyPairs[2]
        self.key2cert = keyPairs[3]
        self.key1pem = "key1.pem"
        self.key2pem = "key2.pem"
        
        # Get files path need to sign or hashsum
        self.GetSignHashFilesList()

        # Move files to their path
        self.CopyFile(tos, self.dir+self.hashSumFiles[1])
        self.MoveFile(self.dir+"EFI/org.clearlinux/loaderx64.efi", self.dir+self.signFiles[1])
        self.CopyFile(self.efiFile, self.dir+self.signFiles[0])

        # Get pem key
        self.GetKeyPem(self.key1, self.key1pem)
        self.GetKeyPem(self.key2, self.key2pem)

        # Main
        self.UpdateEspMainPro()

    def UpdateEspMainPro(self):
        self.SignFiles()
        self.CreateVbmeta()
 
    def __del__(self):
        if os.path.exists(self.key1pem):
            os.remove(self.key1pem)
        if os.path.exists(self.key2pem):
            os.remove(self.key2pem)

    def GetKeyPem(self, key, pem):
        self.Run(["openssl", "pkcs8", "-inform", "DER", "-outform", "PEM", "-nocrypt", "-in", key, "-out", pem], None)

    def SignFiles(self):
        print("SignFiles: ")
        for file in self.signFiles:
            self.Run(["sbsign", "--key", self.key1pem, "--cert", self.key1cert, "--output", self.dir+file+".signed", self.dir+file], None)
            os.remove(self.dir+file)
            self.MoveFile(self.dir+file+".signed", self.dir+file)
            print("         ", file)

    def CreateVbmeta(self):
        iasInputFiles = []
        fileno = 0
        print("HashSumFiles:")
        for hashFile in self.hashSumFiles:
            data = self.Read(self.dir+hashFile)
            hashVal = hashlib.sha256(data) 
            self.Write(hashVal.digest(), str(fileno)+".sha256")
            self.Write(hashFile.replace("/","\\")+"\0", str(fileno)+".path")
            iasInputFiles.append(str(fileno)+".path")
            iasInputFiles.append(str(fileno)+".sha256")
            fileno += 1
            print("             ", hashFile)
        self.Run(["iasimage", "create", "-i", "0x40300", "-d", self.key2pem ] + iasInputFiles+ ["-o", self.dir+"EFI/BOOT/vbmeta.ias", "--page-align=2"], None)
        print("Create vbmeta.ias successful")
        for f in iasInputFiles:
            os.remove(f) 
    
    def GetSignHashFilesList(self):
        loadFilePath = "loader/loader.conf"
        osConfDir = "loader/entries/"
        osOrgDir = "EFI/org.clearlinux/"

        self.signFiles = ["EFI/BOOT/BOOTX64.EFI",
                          "EFI/BOOT/loaderx64.efi"]
        self.hashSumFiles = ["EFI/BOOT/loaderx64.efi",
                             "EFI/BOOT/tos.img"]

        entryFilesList = os.listdir(self.dir+osConfDir)
        loadFile = open(self.dir+loadFilePath, "rb")
        loaderInfo = loadFile.readline()
        while loaderInfo:
            if "default" in loaderInfo:
                break
            loaderInfo = loadFile.readline()
        loadFile.close()
        if "default" not in loaderInfo:
            print("Missing default os.conf in loader.conf")

        for file in entryFilesList:
            (name, suffix) = os.path.splitext(file)
            if name in loaderInfo:
                self.hashSumFiles.append(osConfDir+file)
                osLoaderPath = osConfDir + file
                break

        osLoaderInfo = self.Read(self.dir + osLoaderPath)
        osFilesList = os.listdir(self.dir + osOrgDir)
        for file in osFilesList:
            if file in osLoaderInfo:
                self.hashSumFiles.append(osOrgDir+file)
            if "kernel" in file:
                self.signFiles.append(osOrgDir+file)

def main(esp, efi, tos, keyList):
    if not os.path.exists(esp):
        print("Esp partition folder does not exist")
        exit()
    out = "efi_new_key/"
    if os.path.exists(out):
        print("The efi_new_key dir already exists, please delete it")
        exit()
    shutil.copytree(esp, out)
    rep = ReplaceKey(efi, keyList[3])
    UpdateEsp(out, rep.repKeyEfi, tos, keyList)
    print("The updated Efi partition is stored in efi_new_key dir")

def Note():
    print ("\
           ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n\
           + NOTE:                                                                      +\n\
           +   The script is used to update efi partition for cic host                  +\n\
           +   Details:                                                                 +\n\
           +     1) Replace cic host first stage bootloader(BOOTX64.EFI) with kf4cic.efi+\n\
           +     2) Create vbmeta.ias based on tos.img and other key files              +\n\
           +     3) Sign vbmeta.ias and update public key into BOOTX64.EFI              +\n\
           +     4) Sign BOOTX64.EFI with BIOS key                                      +\n\
           +     5) Add vbmeta.ias and tos.img into ESP folder /EFI/BOOT                +\n\
           +                                                                            +\n\
           +   The code depends on some tools                                           +\n\
           +   1. Sbsign:                                                               +\n\
           +      sudo apt install sbsigntool                                           +\n\
           +   2. iasimage:                                                             +\n\
           +      1) Download iasimage-v002.tar.gz                                      +\n\
           +          Link: https://github.com/intel/iasimage/releases/download/v0.0.2/ +\n\
           +                  iasimage-v0.0.2.tar.gz                                    +\n\
           +      2) Uncompress the iasimage-v002.tar.gz                                +\n\
           +          tar -xvf iasimage-v002.tar.gz                                     +\n\
           +      3) Increase executable permission for iasimage                        +\n\
           +          chmod +x iasimage-v002/iasimage                                   +\n\
           +      4) Push iasimage to env                                               +\n\
           +          cp iasimage-v002/iasimage /usr/bin/                               +\n\
           + PARAM INFO:                                                                +\n\
           +   <esp> CIC host esp partition folder                                      +\n\
           +   <efi> kf4cic.efi can be found in CIC build of Celadon                    +\n\
           +   <tos> tos.img can be found in CIC build of Celadon                       +\n\
           +   <key1>      /device/intel/build/testkeys/DB.pk8                          +\n\
           +   <key1cert>  /device/intel/build/testkeys/DB.x509.pem                     +\n\
           +   <key2>      /device/intel/build/testkeys/xbl_default.pk8                 +\n\
           +   <key2cert>  /device/intel/build/testkeys/xbl_default.x509.pem            +\n\
           +                                                                            +\n\
           +   The intel keys can be replaced by customer                               +\n\
           ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
def Usage():
    print ("\
            Usage: \n\
            python update_esp.py <esp> <efi> <tos> <key1> <key1cert> <key2> <key2cert>")

if __name__ == "__main__":
    if sys.argv[1] == "--help" or sys.argv[1] == "-h":
        Note()
    if len(sys.argv) != 8:
        Usage()
        exit()
    
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
