import os
import subprocess
import struct
import binascii
import string
import tempfile
from pyasn1.codec.ber import decoder as ber_decoder
from pyasn1_modules import rfc2315 as pkcs7

class Options():
    pass
OPTIONS = Options()
OPTIONS.verbose = False
OPTIONS.legacy = False
OPTIONS.ignore_legacy = False
OPTIONS.signfile_path_env = "SIGNFILE_PATH"



def Run(args, **kwargs):
    """Create and return a subprocess.Popen object, printing the command
    line on the terminal if -v was specified."""
    if OPTIONS.verbose:
        print("  running: ", " ".join(args))
    return subprocess.Popen(args, **kwargs, shell=False)


SIGNER_TYPE_UNKNOWN = 0
SIGNER_TYPE_PEM = 1
SIGNER_TYPE_PKCS8 = 2
SIGNER_TYPE_CSS = 3


def DetectSignerType(privkey_filename):
    keyfile = open(privkey_filename, "rb")
    canary_byte = keyfile.read(1)
    keyfile.close()
    if canary_byte == "\x30":
        # Found ASN.1 'sequence' indicator. Assume PKCS #8 DER format.
        return SIGNER_TYPE_PKCS8
    if canary_byte == "-":
        # Found character at start of a PEM block. Assume PEM format.
        return SIGNER_TYPE_PEM
    if canary_byte[0] in string.printable:
        # Found a printable character. Assume file containing CSS key name.
        return SIGNER_TYPE_CSS
    return SIGNER_TYPE_UNKNOWN


# To generate signature with OpenSSL
#  openssl dgst -DIGEST_NAME -binary CANDIDATE_FILE |
#   openssl pkeyutl -sign -keyform DER -inkey PKCS8_FILE \
#       -pkeyopt digest:DIGEST_NAME
#
# To verify signature with OpenSSL
#  openssl dgst -DIGEST_NAME -binary CANDIDATE_FILE |
#   openssl pkeyutl -verify -inkey PEM_FILE -sigfile SIGNATURE_FILE
def DoSign(candidate_filename, privkey_filename,
           digest_name,  privkey_password=None):
    sign_type = DetectSignerType(privkey_filename)

    if sign_type == SIGNER_TYPE_PEM or sign_type == SIGNER_TYPE_PKCS8:
        format_spec = "DER" if sign_type == SIGNER_TYPE_PKCS8 else "PEM"

        # openssl pkeyutl does not support passwords for pk8 -- only PEM --
        # so convert to PEM in a temp file and use the temp file
        if format_spec == "DER" and privkey_password is not None:
            pem_privkey = tempfile.NamedTemporaryFile()
            p0 = Run(["openssl", "pkcs8",
                      "-inform", "DER",
                      "-outform", "PEM",
                      "-passin", "stdin",
                      "-in", privkey_filename,
                      "-out", pem_privkey.name],
                      stdin=subprocess.PIPE)
            p0.communicate(privkey_password+"\n")
            assert p0.returncode == 0, ("openssl pkcs8 of %s failed" %
                                        privkey_filename)
            format_spec = "PEM"
            privkey_filename = pem_privkey.name

        dgstfile = tempfile.NamedTemporaryFile()
        p1 = Run(["openssl",
                  "dgst", "-" + digest_name,
                  "-binary", "-out", dgstfile.name,
                  candidate_filename])
        p1.wait()
        assert p1.returncode == 0, ("openssl dgst of %s failed" %
                                    (candidate_filename,))
        pkeyutl_cmd = ["openssl",
                       "pkeyutl", "-sign",
                       "-in", dgstfile.name]
        if privkey_password is not None:
            pkeyutl_cmd.extend(["-passin", "stdin"])
        pkeyutl_cmd.extend(["-keyform", format_spec,
                            "-inkey", privkey_filename,
                            "-pkeyopt", "digest:" + digest_name])
        p2 = Run(pkeyutl_cmd,
                 stdin=subprocess.PIPE,
                 stderr=subprocess.PIPE,
                 stdout=subprocess.PIPE)
        if privkey_password is not None:
            privkey_password += '\n'
        (sig, err) = p2.communicate(privkey_password)
        print(err)
        assert p2.returncode == 0, ("openssl pkeyutl of %s failed" %
                                    (candidate_filename,))

    elif sign_type == SIGNER_TYPE_CSS:
        signfile_path = os.environ[OPTIONS.signfile_path_env] + "SignFile"

        # Get the CSS key name from the private key file
        privkey_file = open(privkey_filename)
        signer_cert_name = privkey_file.readline().strip()
        privkey_file.close()

        # Create a temporary file for the signature output
        signature_file = tempfile.NamedTemporaryFile(delete=False)
        signature_file_name = signature_file.name
        signature_file.close()

        p1 = Run([signfile_path,
                  "-s", "cl",
                  "-ts", "-vv",
                  "-ha", digest_name.upper(),
                  "-cf", signature_file_name,
                  "-c", signer_cert_name,
                  candidate_filename],
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p1.communicate()
        if OPTIONS.verbose:
            print(out)
            print(err)
        assert p1.returncode == 0, ("%s signing of %s failed" %
                                    (signfile_path, candidate_filename))

        # Read the signature result and pull out the signature block
        signature_file = open(signature_file_name, "rb")
        sig_content_data = signature_file.read()
        signature_file.close()
        os.remove(signature_file_name)
        (content, remain) = ber_decoder.decode(sig_content_data,
                                               asn1Spec=pkcs7.ContentInfo())
        assert content.getComponentByName('contentType') == pkcs7.signedData, (
                "%s output is not expected PKCS #7 SignedData" % signfile_path)
        (content, remain) = ber_decoder.decode(content.getComponentByName('content'),
                                               asn1Spec=pkcs7.SignedData())
        sig = content.getComponentByName('signerInfos')[0].getComponentByName('encryptedDigest').asOctets()

    else:
        print("Sign type:", sign_type)
        assert False, "%s does not contain a recognized key." % privkey_filename

    return sig


# To generate signature with OpenSSL
#  openssl dgst -DIGEST_NAME -binary CANDIDATE_FILE |
#   openssl pkeyutl -sign -keyform DER -inkey PKCS8_FILE \
#       -pkeyopt digest:DIGEST_NAME
#
# To verify signature with OpenSSL
#  openssl dgst -DIGEST_NAME -binary CANDIDATE_FILE |
#   openssl pkeyutl -verify -inkey PEM_FILE -sigfile SIGNATURE_FILE
def DoVerify(candidate_filename, signature_filename,
             digest_name, cert_filename):
    p1 = Run(["openssl",
              "dgst", "-" + digest_name,
              "-binary", candidate_filename], stdout=subprocess.PIPE)
    p2 = Run(["openssl",
              "pkeyutl", "-verify",
              "-certin", "-keyform", "PEM", "-inkey", cert_filename,
              "-sigfile", signature_filename,
              "-pkeyopt", "digest:" + digest_name],
              stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p2.communicate()
    p1.wait()
    assert p1.returncode == 0, ("openssl dgst of %s failed" %
                                (candidate_filename,))
    if OPTIONS.verbose:
        print(out)
        print(err)

    # openssl pkeyutl has a bug that always returns 1 regardless of verify
    # success or failure, so check the output against the know success string
    return out.strip() == "Signature Verified Successfully"


def copy_file_bytes(infile, outfile, num_bytes, block_size=(1024 * 64)):
    remaining_size = num_bytes
    buf = infile.read(min(remaining_size, block_size))
    while len(buf) == block_size:
        remaining_size -= block_size
        outfile.write(buf)
        buf = infile.read(min(remaining_size, block_size))
    if len(buf) != remaining_size:
        raise EOFError("Unexpected end of file")
    outfile.write(buf)

    return remaining_size


def process_page_buffer(buf, page_size, infile, outfile):
    outfile.write(buf)
    padlen = (page_size - (len(buf) % page_size)) % page_size

    process_page_padding(infile, outfile, padlen)
    return len(buf) + padlen


def process_page_file(sectionlen, page_size, infile, outfile):
    try:
        remaining_size = copy_file_bytes(infile, outfile, sectionlen, page_size)
    except EOFError:
        raise BootimgFormatException("Unexpected end of file (header incorrect?)")

    padlen = (page_size - remaining_size) % page_size
    process_page_padding(infile, outfile, padlen)

    return sectionlen + padlen


def process_page_padding(infile, outfile, padlen):
    if padlen == 0:
        return

    if infile:
        # read what should be either padlen bytes of pad, or EOF
        padbuf = infile.read(padlen)
        if len(padbuf) != padlen and padlen != 0:
            raise BootimgFormatException(
                "Unexpected section padding; expected 0 or %d, found %d" % (
                    padlen, len(padbuf)))
    else:
        padbuf = ""

    # verify the content of the pad
    if len(padbuf) == 0:
        padbuf = "\x00" * padlen
    elif len(padbuf.strip("\x00")) != 0:
        # test by stripping characters. If any remain, the pad is invalid
        raise BootimgFormatException(
            "Unexpected section padding; non-zero bytes found")

    # write pad to output
    outfile.write(padbuf)


# From hardware/intel/mkbootimg_secure/bootimg.h, which is derived from
# system/core/mkbootimg/bootimg.h.
#
# Differences from system/core/mkbootimg/bootimg.h are the following:
#  - First unsigned of the 'unused' field is replaced with 'sig_size' in
#    initial Intel format
#  - 'extra_cmdline' appears at the end of the header
#
# #define BOOT_MAGIC "ANDROID!"
# #define BOOT_MAGIC_SIZE 8
# #define BOOT_NAME_SIZE 16
# #define BOOT_ARGS_SIZE 512
# #define BOOT_EXTRA_ARGS_SIZE 1024
#
# struct boot_img_hdr
# {
#     unsigned char magic[BOOT_MAGIC_SIZE];
#
#     unsigned kernel_size;  /* size in bytes */
#     unsigned kernel_addr;  /* physical load addr */
#
#     unsigned ramdisk_size; /* size in bytes */
#     unsigned ramdisk_addr; /* physical load addr */
#
#     unsigned second_size;  /* size in bytes */
#     unsigned second_addr;  /* physical load addr */
#
#     unsigned tags_addr;    /* physical addr for kernel tags */
#     unsigned page_size;    /* flash page size we assume */
#     unsigned sig_size;     /* if initial Intel signature format:
#                                 bootimage signature size or 0 */
#     unsigned unused;       /* future expansion: should be 0 */
#
#     unsigned char name[BOOT_NAME_SIZE]; /* asciiz product name */
#
#     unsigned char cmdline[BOOT_ARGS_SIZE];
#
#     unsigned id[8]; /* timestamp / checksum / sha1 / etc */
#
#     /* Supplemental command line data; kept here to maintain
#      * binary compatibility with older versions of mkbootimg */
#     unsigned char extra_cmdline[BOOT_EXTRA_ARGS_SIZE];
# };
#
#
# +-----------------+
# | boot header     | 1 page
# +-----------------+
# | kernel          | n pages
# +-----------------+
# | ramdisk         | m pages
# +-----------------+
# | second stage    | o pages
# +-----------------+
# | signature       | p pages
# +-----------------+
#
# n = (kernel_size + page_size - 1) / page_size
# m = (ramdisk_size + page_size - 1) / page_size
# o = (second_size + page_size - 1) / page_size
# p = (sig_size + page_size - 1) / page_size
#
# 0. all entities are page_size aligned in flash
# 1. kernel and ramdisk are required (size != 0)
# 2. second is optional (second_size == 0 -> no second)
# 3. load each element (kernel, ramdisk, second) at
#    the specified physical address (kernel_addr, etc)
# 4. prepare tags at tag_addr.  kernel_args[] is
#    appended to the kernel commandline in the tags.
# 5. r0 = 0, r1 = MACHINE_TYPE, r2 = tags_addr
# 6. if second_size != 0: jump to second_addr
#    else: jump to kernel_addr
# 7. signature is optional; size should be 0 if not
#    present. signature type specified by bootloader
#

class BootimgFormatException(Exception):
    """Exception raised for errors format of input boot images.

    Attributes:
        msg  -- explanation of the error
    """

    def __init__(self, msg):
        self.msg = msg


class BootimgHeader():
    __BOOTIMG_PACK_FORMAT = "8s10I16s512s32s1024s"
    __header_parser = struct.Struct(__BOOTIMG_PACK_FORMAT)
    BOOTIMG_HEADER_SIZE = __header_parser.size
    BOOTIMG_MAGIC = "ANDROID!"

    def __init__(self, src, options):
        force_unused0 = False
        buf = src.read(BootimgHeader.BOOTIMG_HEADER_SIZE)
        if len(buf) != BootimgHeader.BOOTIMG_HEADER_SIZE:
            raise BootimgFormatException("Not a valid boot image (incomplete header)")

        h = {}
        (h["magic"],
         h["kernel_size"], h["kernel_addr"],
         h["ramdisk_size"], h["ramdisk_addr"],
         h["second_size"], h["second_addr"],
         h["tags_addr"],
         h["page_size"],
         h["unused0"],
         h["unused1"],
         h["product_name"],
         h["cmdline"],
         h["img_id"],
         h["extra_cmdline"]) = BootimgHeader.__header_parser.unpack(buf)
        # print h
        self.header_buf = buf
        for key in h:
            setattr(self, key, h[key])

        if self.magic != BootimgHeader.BOOTIMG_MAGIC:
            raise BootimgFormatException(
                "Not a valid boot image (magic mismatch)")
        if self.page_size < BootimgHeader.BOOTIMG_HEADER_SIZE:
            raise BootimgFormatException(
                "'page_size' must be at least the size of the header (>=%d)" % BootimgHeader.BOOTIMG_HEADER_SIZE)
        if self.unused0 != 0:
            # Original Intel signature used this field to indicate signature length
            if not options.legacy and not options.ignore_legacy:
                raise BootimgFormatException("Invalid header (Unused[0] is not zero). Use --legacy or --ignore-legacy")
            else:
                force_unused0 = True
        if self.unused1 != 0:
            raise BootimgFormatException("Invalid header (Unused[1] is not zero)")
        if self.ramdisk_size == 0 or self.kernel_size == 0:
            raise BootimgFormatException("Invalid boot image (empty ramdisk or kernel")

        # If legacy mode is being used, tweak the header to treat 'unused0'
        # as 'sig_size'.
        if options.legacy:
            self.header_buf = buf[0:40] + struct.pack("I", options.legacy_siglen / 8) + buf[44:]
        elif force_unused0:
            self.header_buf = buf[0:40] + struct.pack("I", 0) + buf[44:]

    def __str__(self):
        s = ("=" * 75) + "\n"
        s += "             Magic: %s\n" % self.magic
        s += "  Kernel size/addr: %d/0x%08X\n" % (self.kernel_size,
                                                      self.kernel_addr)
        s += " Ramdisk size/addr: %d/0x%08X\n" % (self.ramdisk_size,
                                                      self.ramdisk_addr)
        s += "  Second size/addr: %d/0x%08X\n" % (self.second_size,
                                                      self.second_addr)
        s += "         Tags addr: 0x%08X\n" % self.tags_addr
        s += "         Page size: %d\n" % self.page_size
        s += "            Unused: 0x%08X %08X\n" % (self.unused0,
                                                    self.unused1)
        s += "      Product name: %s\n" % self.product_name.rstrip("\x00")
        s += "      Command line: %s\n" % self.cmdline.rstrip("\x00")
        s += "                ID: %s\n" % binascii.hexlify(self.img_id)
        s += "Extra command line: %s\n" % self.extra_cmdline.rstrip("\x00")
        s += "=" * 75
        return s


