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
import sys
import struct
import argparse
import collections
import binascii
import Crypto.PublicKey.RSA
import Crypto.Signature.PKCS1_v1_5
import Crypto.Util

# typedef struct {
#   uint32_t KeyType;             // (LE) Key type: 0 = Production key.
#                                 //                1 = Development key.
#                                 //                2 = Gold key.
#   uint32_t KeyLength;           // (LE) Bit size key (1024, 1536, 2048).
#   uint32_t Exponent;            // (LE) Public key exponent (3 or 65537).
#   uint8_t  Modulus[256];        // (LE) Modulus of public key.
#   uint8_t  Montgom[256];        // (LE) Montgomery factor.
# } PublicKeyStructType;
SF_PUBKEY_PACK_FMT = '<III256s256s'
sf_pubkey_struct = struct.Struct(SF_PUBKEY_PACK_FMT)
PublicKeyStruct = collections.namedtuple('PublicKeyStruct', 'key_type key_length exponent modulus montgom')
SF_VALID_PUBLIC_EXPONENTS = [0x010001L, 3L]

SF_KEYTYPE_PRODUCTION   = 0
SF_KEYTYPE_DEVELOPMENT  = 1
SF_KEYTYPE_GOLD         = 2

SF_KEYTYPE_IMCGOLD      = 100
SF_KEYTYPE_IMCGOLD_MONT = 101

# typedef struct {
#   uint32_t PrivateDigest[5];    // (LE) SHA1 of private key structure.
#   uint32_t KeyType;             // (LE) Key type: 0 = Production key.
#                                 //                1 = Development key.
#                                 //                2 = Gold key.
#   uint32_t KeyMarker;           // (LE) Magic number: 0xAABBCCDD.
#   uint32_t KeyLength;           // (LE) Bit size key (1024, 1536, 2048).
#   uint8_t  Exponent[256];       // (BE) Exponent of private key.
#   uint8_t  Modulus[256];        // (BE) Modulus of private key.
#   uint32_t PublicDigest[5];     // (LE) SHA1 of public key structure.
# } PrivateKeyStructType;
SF_PRIVKEY_PACK_FMT = '<20sIII256s256s20s'
sf_privkey_struct = struct.Struct(SF_PRIVKEY_PACK_FMT)
PrivateKeyStruct = collections.namedtuple('PrivateKeyStruct', 'private_digest key_type key_marker key_length exponent modulus public_digest')
SF_PRIVKEY_KEY_MARKER = 0xAABBCCDD

# typedef struct {
#   uint32_t KeyLength;           // (LE) Bit size key (1024, 1536, 2048).
#   uint32_t Exponent;            // (LE) Public key exponent (3 or 65537).
#   uint8_t  Modulus[256];        // (LE) Modulus of public key.
# } GoldKeyStructNoMontgomeryType;
#
# typedef struct {
#   uint32_t KeyLength;           // (LE) Bit size key (1024, 1536, 2048).
#   uint32_t Exponent;            // (LE) Public key exponent (3 or 65537).
#   uint8_t  Modulus[256];        // (LE) Modulus of public key.
#   uint8_t  Montgom[256];        // (LE) Montgomery factor.
# } GoldKeyStructWithMontgomeryType;
SF_GOLD_PUBKEY_NO_MONTGOMERY_PACK_FMT = '<II256s'
sf_gold_pubkey_no_montgomery_struct = struct.Struct(SF_GOLD_PUBKEY_NO_MONTGOMERY_PACK_FMT)
SF_GOLD_PUBKEY_WITH_MONTGOMERY_PACK_FMT = '<II256s256s'
sf_gold_pubkey_with_montgomery_struct = struct.Struct(SF_GOLD_PUBKEY_WITH_MONTGOMERY_PACK_FMT)

def key_struct_to_RSA(key_parts):
    key = None

    if (isinstance(key_parts, PublicKeyStruct)):
        try:
            # Public key structure has modulus in little-endian order, so reverse bytes
            key = Crypto.PublicKey.RSA.construct(
                            (Crypto.Util.number.bytes_to_long(key_parts.modulus[::-1]),
                             key_parts.exponent))
        except ValueError:
            print '** Error: public key data invalid!'
            exit(1)

    else:
        # try each valid public exponent until we find one that works
        for e in SF_VALID_PUBLIC_EXPONENTS:
            try:
                # Private key structure has modulus and exponent in big-endian order
                parts_tuple = (Crypto.Util.number.bytes_to_long(key_parts.modulus),
                               e,
                               Crypto.Util.number.bytes_to_long(key_parts.exponent))
                key = Crypto.PublicKey.RSA.construct(parts_tuple)
            except ValueError:
                pass
        if key is None:
            print '** Error: None of the valid public exponents create a valid key'
            exit(1)

    if key.e < 0x010001:
        print '** Warning: public key has weak exponent!'

    return key

DATATYPE_DER_KEY         = 1
DATATYPE_DER_CERT_PUBLIC = 2
DATATYPE_PEM_ANY         = 50
DATATYPE_UNKNOWN         = 100

def get_data_type_by_filename(filename):
    if filename.endswith('.pk8') or filename.endswith('.pk1'):
        return DATATYPE_DER_KEY
    if filename.endswith('.cer'):
        return DATATYPE_DER_CERT_PUBLIC
    if filename.endswith('.pem'):
        return DATATYPE_PEM_ANY
    return DATATYPE_UNKNOWN

'''
Interogates parsed command line arguments to determine how an input file
should be interpretted.
'''
def get_input_type(args):
    if args.src_type != DATATYPE_UNKNOWN:
        return src_type
    return get_data_type_by_filename(args.src)

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
        print '** Error: key data not recognized'
        exit(1)

def get_RSA_from_PEM(data):
    if data.startswith('-----BEGIN CERTIFICATE-----'):
        der_data = pem_to_der(data)
        return get_RSA_from_x509(der_data)
    elif data.startswith('-----BEGIN PRIVATE KEY-----') or data.startswith('-----BEGIN PUBLIC KEY-----'):
        return get_RSA_from_key_blob(data)
    else:
        print '** Data is not a PEM object'
        return None

def get_sofia_public_key(key, sf_key_type):
    # compute the montgomery factor
    R = (1L << (key.size() + 1))
    montgomery_factor = (R ** 2) % key.n

    if sf_key_type is None:
        sf_key_type = SF_KEYTYPE_DEVELOPMENT
    # pycrypto's RSA.size() returns the bit size of the largest message
    # that can be encrypted with the key, which is one bit lower than the
    # key size.
    key_size = key.size() + 1
    exponent = int(key.e)
    # Sofia public keys store the modulus and montgomery factor little-endian,
    # so reverse the bytes
    modulus = Crypto.Util.number.long_to_bytes(key.n, 256)[::-1]
    montgomery = Crypto.Util.number.long_to_bytes(montgomery_factor, 256)[::-1]

    if (sf_key_type == SF_KEYTYPE_IMCGOLD):
        pubkey = sf_gold_pubkey_no_montgomery_struct.pack(key_size, exponent, modulus)
    elif (sf_key_type == SF_KEYTYPE_IMCGOLD_MONT):
        pubkey = sf_gold_pubkey_with_montgomery_struct.pack(key_size, exponent, modulus, montgomery)
    else:
        pubkey = sf_pubkey_struct.pack(sf_key_type, key_size, exponent, modulus, montgomery)
    return pubkey


def convert_std2sf(args):
    # read content of input file
    with open(args.src, "rb") as src_file:
        src_data = src_file.read()

    data_type = get_input_type(args)
    if (data_type == DATATYPE_PEM_ANY):
        key = get_RSA_from_PEM(src_data)
    elif (data_type == DATATYPE_DER_KEY):
        key = get_RSA_from_key_blob(src_data)
    elif (data_type == DATATYPE_DER_CERT_PUBLIC):
        key = get_RSA_from_x509(src_data)
    else:
        print "** Error: don't know how to parse input data"
        exit(1)

    # export Xpub.key
    with open(args.dest + "puk.key", "wb") as pubkey_file:
        pubkey_file.write(get_sofia_public_key(key, args.sf_key_type))


def convert_sf2std(args):
    # read content of input file
    with open(args.src, "rb") as src_file:
        src_data = src_file.read()

    # try to guess the type based on binary length
    if len(src_data) == sf_privkey_struct.size:
        print 'source is private key'
        key_parts = PrivateKeyStruct._make(sf_privkey_struct.unpack(src_data))
        if key_parts.key_marker != SF_PRIVKEY_KEY_MARKER:
            print '**** Private key magic number is wrong!'
            exit(2)

        # try each valid public exponent until we find one that works
        key = key_struct_to_RSA(key_parts)

        # ensure the created key actually works
        digest = Crypto.Hash.SHA256.new("abc")
        sig_scheme = Crypto.Signature.PKCS1_v1_5.new(key)
        signature = sig_scheme.sign(digest)
        if sig_scheme.verify(digest, signature):
            print 'key signs and verifies'
        else:
            print 'key does not work!'

        # export PK8 blob
        with open(args.dest + ".pk8", "wb") as privkey_file:
            privkey_file.write(key.exportKey(format='DER', pkcs=8))

        # export public key
        with open(args.dest + "_pub.pem", "wb") as pubkey_file:
            pubkey_file.write(key.publickey().exportKey(format='PEM', pkcs=1))

    elif len(src_data) == sf_pubkey_struct.size:
        print 'source is public key'
        key_parts = PublicKeyStruct._make(sf_pubkey_struct.parse(src_data))

        key = key_struct_to_RSA(key_parts)

        with open(args.dest + "_pub.pem", "wb") as pubkey_file:
            pubkey_file.write(key.exportKey(format='PEM', pkcs=1))

    else:
        print "source doesn't seem to be a key"
        exit(1)

def main(argv):
    parser = argparse.ArgumentParser(description='Convert key formats between standard and SoFIA')
    subparsers = parser.add_subparsers()

    # sd2std command
    sf2std_parser = subparsers.add_parser('sf2std', help='convert from SoFIA format to PEM/PK8')
    sf2std_parser.add_argument('src', metavar='SRC', help='puk/prk key to convert',
                               action='store')
    sf2std_parser.add_argument('dest', metavar='DEST', help='base name for converted key files (puk.key suffix added)',
                               action='store')
    sf2std_parser.set_defaults(dofunc=convert_sf2std)

    # std2sf command
    std2sf_parser = subparsers.add_parser("std2sf", help='convert from PEM/PK8 to SoFIA public key format')
    std2sf_parser.add_argument('src', metavar='SRC', help='PEM/PK1 key to convert (.pem, .pk1, .cer file)',
                               action='store')
    std2sf_parser.add_argument('dest', metavar='DEST', help='base name for converted key files (puk.key suffix added)',
                               action='store')
    std2sf_parser.set_defaults(dofunc=convert_std2sf)

    # Input format cues for std2sf
    action_group = std2sf_parser.add_argument_group(title="input formats")
    action_parser = action_group.add_mutually_exclusive_group(required=False)
    action_parser.add_argument('--input-pem', help='force interpretation of input as a PEM file',
                               action='store_const', dest='src_type', const=DATATYPE_PEM_ANY)
    action_parser.add_argument('--input-der', help='force interpretation of input as a DER blob',
                               action='store_const', dest='src_type', const=DATATYPE_DER_KEY)
    action_parser.add_argument('--input-x509', help='force interpretation of input an X.509v3 DER blob',
                               action='store_const', dest='src_type', const=DATATYPE_DER_CERT_PUBLIC)
    action_parser.set_defaults(src_type=DATATYPE_UNKNOWN)

    # Sofia key type for std2sf
    action_group = std2sf_parser.add_argument_group(title="output key types")
    action_parser = action_group.add_mutually_exclusive_group(required=False)
    action_parser.add_argument('--output-prod', help='output key blobs with "production" tag',
                               action='store_const', dest='sf_key_type', const=SF_KEYTYPE_PRODUCTION)
    action_parser.add_argument('--output-dev', help='output key blobs with "development" tag',
                               action='store_const', dest='sf_key_type', const=SF_KEYTYPE_DEVELOPMENT)
    action_parser.add_argument('--output-gold', help='output key blobs with "gold" tag',
                               action='store_const', dest='sf_key_type', const=SF_KEYTYPE_GOLD)
    action_parser.add_argument('--output-imcgold', help='output key blob to exchange with IMC Trust Center, no Montgomery factor',
                               action='store_const', dest='sf_key_type', const=SF_KEYTYPE_IMCGOLD)
    action_parser.add_argument('--output-imcgold-mont', help='output key blob to exchange with IMC Trust Center with Montgomery factor',
                               action='store_const', dest='sf_key_type', const=SF_KEYTYPE_IMCGOLD_MONT)
    action_parser.set_defaults(sf_key_type=SF_KEYTYPE_DEVELOPMENT)


    args = parser.parse_args(argv)
    args.dofunc(args)

if __name__ == '__main__':
    main(sys.argv[1:])