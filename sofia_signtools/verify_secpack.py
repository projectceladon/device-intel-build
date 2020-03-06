#!/usr/bin/env python

# Copyright 2015 Intel Corporations
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Verifies the contents of an FLS using supplied M and G public keys.
This is primarily a vehicle for understanding the details of signature
formats for development purposes.
"""
import sys
import struct
import argparse
import collections
import binascii
import Crypto.PublicKey.RSA
import Crypto.Signature.PKCS1_v1_5
import Crypto.Util
import Crypto.Hash.hashalgo
import Crypto.Hash.SHA
import Crypto.Hash.SHA256

SECPACK_PACK_FMT = "<256s256sI135s?II32s32sIII24s20s"
MIN_SECPACK_LEN = 2048

class GoofyHash(Crypto.Hash.hashalgo.HashAlgo):
    """Wraps a pycrypto hash algorithm instance to return a "goofy" hash
    value, where each 32 bit word in the output has least significant byte
    first.
    """

    def __init__(self, inner):
        self.__inner = inner
        self.oid = inner.oid

    def update(self, data):
        self.__inner.update(data)

    def digest(self):
        orig = self.__inner.digest()

        num_words = len(orig) / 4
        unpack_fmt = "<" + ("I" * num_words)
        pack_fmt = ">" + ("I" * num_words)

        words = struct.unpack(unpack_fmt, orig)
        #print words
        return struct.pack(pack_fmt, *words)

    def hexdigest(self):
        orig = self.digest()
        return "".join("{:02x}".format(ord(c)) for c in orig)

    def copy(self):
        return GoofyHash(self.__inner.copy())

    def new(self, data=None):
        return GoofyHash(self.__inner.new(data))

def pem_to_der(pem_data):
    no_spaces = pem_data.replace(' ', '')
    lines = no_spaces.split()
    no_headers = lines[1:-1]
    return binascii.a2b_base64(''.join(no_headers))


def get_RSA_from_x509(der_data):
    # pull apart the cert enough to extract the public key
    cert = Crypto.Util.asn1.DerSequence()
    cert.decode(der_data)
    tbsCertificate = Crypto.Util.asn1.DerSequence()
    tbsCertificate.decode(cert[0])
    subjectPublicKeyInfo = tbsCertificate[6]

    return get_RSA_from_key_blob(subjectPublicKeyInfo)

def get_RSA_from_key_blob(data):
    try:
        return Crypto.PublicKey.RSA.importKey(data)
    except (ValueError, TypeError, IndexError):
        print('** Error: key data not recognized')
        exit(1)

def get_RSA_from_PEM(data):
    if data.startswith('-----BEGIN CERTIFICATE-----'):
        der_data = pem_to_der(data)
        return get_RSA_from_x509(der_data)
    elif data.startswith('-----BEGIN PRIVATE KEY-----') or data.startswith('-----BEGIN PUBLIC KEY-----'):
        return get_RSA_from_key_blob(data)
    else:
        print('** Data is not a PEM object')
        return None

def hex_string(byte_str):
    return "".join("{:02x}".format(ord(c)) for c in byte_str)

def try_verify_all_combinations(what_str, verbose, key, data, sig):
    digest256 = Crypto.Hash.SHA256.new(data)
    goofy_digest256 = GoofyHash(digest256)

    sig_reverse = sig[::-1]

    if verbose:
        print("{} details".format(what_str))
        print("  {} ".format(what_str), hex_string(sig))

        try:
            insides = key.encrypt(sig, 0)
            print("  {} decrypted ".format(what_str), hex_string(insides[0]))
        except:
            print("  {} does not decrypt".format(what_str))

        try:
            insides = key.encrypt(sig_reverse, 0)
            print("  {} reversed decrypted ".format(what_str), hex_string(insides[0]))
        except:
            print("  {} reversed does not decrypt".format(what_str))

        print("  std SHA256 ", digest256.hexdigest())
        print("  goofy SHA256 ", goofy_digest256.hexdigest())

    verified = False
    try:
        if Crypto.Signature.PKCS1_v1_5.new(key).verify(digest256, sig):
            verified = True
            print("==> verified {} std SHA256".format(what_str))
    except:
        pass

    try:
        if not verified and Crypto.Signature.PKCS1_v1_5.new(key).verify(digest256, sig_reverse):
            verified = True
            print("==> verified {} reversed std SHA256".format(what_str))
    except:
        pass

    try:
        if not verified and Crypto.Signature.PKCS1_v1_5.new(key).verify(goofy_digest256, sig):
            verified = True
            print("==> verified {} goofy SHA256".format(what_str))
    except:
        pass

    try:
        if not verified and Crypto.Signature.PKCS1_v1_5.new(key).verify(goofy_digest256, sig_reverse):
            verified = True
            print("==> verified {} reversed goofy SHA256".format(what_str))
    except:
        pass

    return verified

def main(argv):
    parser = argparse.ArgumentParser(description='Verify a SECPACK signature')

    parser.add_argument('secpack', metavar='SECPACK', help='SECPACK file to check',
                        action='store')
    parser.add_argument('pubkey', metavar='PUBKEY', help='public key as a PEM certificate or public key',
                        action='store')
    parser.add_argument('--payload', help='payload to check against verified SECPACK',
                        action='store', default=None)
    parser.add_argument('--verbose', help='print internal signature details as they are checked',
                        action='store_const', const=True, default=False)
    parser.add_argument('--psi', help='attempt to verify a PSI signature',
                        action='store_const', const=True, default=False)
    parser.add_argument('--gold-key', metavar='GOLDPUB', help='gold public key for PSI verification',
                        action='store')
    args = parser.parse_args(argv)

    with open(args.pubkey, "rb") as key_file:
        pem_key = key_file.read()
        key = get_RSA_from_PEM(pem_key)
        if (key is None):
            exit(1)

    with open(args.secpack) as secpack_file:
        secpack = secpack_file.read()
        if len(secpack) < MIN_SECPACK_LEN:
            print("** SECPACK is too short")
            exit(1)

    key_parts = struct.unpack_from(SECPACK_PACK_FMT, secpack, 0)
    sig1 = key_parts[0]
    sig2 = key_parts[1]
    digest = key_parts[8]

    tbs_secpack = secpack[512::]

    verified = try_verify_all_combinations("secpack sig1", args.verbose, key, tbs_secpack, sig1) or try_verify_all_combinations("secpack sig2", args.verbose, key, tbs_secpack, sig2)

    if (verified or args.psi) and args.payload is not None:
        with open(args.payload, "rb") as payload_file:
            payload = payload_file.read()

    if verified and args.payload is not None:

        payload_hash = Crypto.Hash.SHA256.new(payload)
        goofy_payload_hash = GoofyHash(payload_hash)
        if args.verbose:
            print("secpack payload hash ", hex_string(digest))
            print("payload std hash ", payload_hash.hexdigest())
            print("payload goofy hash ", goofy_payload_hash.hexdigest())

        verified = False
        if payload_hash.digest() == digest:
            verified = True
            print("==> payload std SHA256 hash matches secpack")
        else:
            if goofy_payload_hash.digest() == digest:
                verified = True
                print("==> payload goofy SHA256 hash matches secpack")

    if args.psi and args.payload is not None:
        if args.gold_key is None:
            print("*** must give --gold-key to verify PSI")
            exit(1)

        with open(args.gold_key, "rb") as key_file:
            pem_key = key_file.read()
            gold_key = get_RSA_from_PEM(pem_key)
            if (gold_key is None):
                exit(1)

        payload_tbs = payload[0:len(payload) - len(sig1)]
        payload_sig = payload[-len(sig1):]

        try_verify_all_combinations("psi sig", args.verbose, key, payload_tbs, payload_sig)


if __name__ == '__main__':
    main(sys.argv[1:])