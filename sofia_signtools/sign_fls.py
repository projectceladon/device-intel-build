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
import argparse
import os
import subprocess
import sys
import tempfile
import Crypto.Hash.SHA256

import fls

options = argparse.Namespace(verbose =False)

# Signer script syntax:
# signer --sign-hash|--sign-data HASH_TYPE KEY_PATH DATA_PATH OUT_SIG_PATH
#
# HASH_TYPE is one of [SHA256]
# KEY_PATH is the filename of the key file to use. The content of the key
#   file may be signer specific.
# DATA_PATH is the input data. If --sign-hash is specified, the content is
#   the hash value to sign. If --sign-data is specified, the content is the
#   raw data to be digested and signed by the provider.
# OUT_SIG_PATH is the resulting signature. It must be the signature value
#   in big-endian (standard) order with no additional data.

def run_and_wait(args, **kwargs):
    if options.verbose:
        print("  running: ", " ".join(args))
    subprocess.check_call(args, **kwargs)


# Format specifications:
# goofy_hash=False, little_endian_sig=True
#   Standard PKCS #1 v1.5 in little-endian order.
#   e.g. PSI signatures
# goofy_hash=False, little_endian_sig=False
#   Standard PKCS #1 v1.5 in big-endian (standard/natural) order.
# goofy_hash=True, little_endian_sig=False
#   PKCS #1 v1.5-ish w/goofy hash in big-endian order.
#   e.g. SecPack signatures
# goofy_hash=True, little_endian_sig=True
#   This is all messed up. You shouldn't be using this.
def do_signature(tbs_data, key_path, goofy_hash=False, little_endian_sig=False):
    tmp_tbs = tempfile.NamedTemporaryFile(prefix='tmptbs_')
    if goofy_hash:
        digest = fls.GoofyHash(Crypto.Hash.SHA256.new(tbs_data))
        tmp_tbs.write(digest.digest())
    else:
        tmp_tbs.write(tbs_data)
    tmp_tbs.flush()

    tmp_sig = tempfile.NamedTemporaryFile(prefix='tmpsig_')

    cmd = [options.sign_exec]
    if goofy_hash:
        cmd.append('--sign-hash')
    else:
        cmd.append('--sign-data')
    cmd.extend(['SHA256', key_path, tmp_tbs.name, tmp_sig.name])
    run_and_wait(cmd)

    sig = tmp_sig.read()
    if little_endian_sig:
        sig = sig[::-1]

    return sig


def main(argv):
    parser = argparse.ArgumentParser(description='Sign an FLS file')
    parser.add_argument('--psi', metavar='GOLD_KEY',
                        help='sign the LoadMap0 binary using GOLD_KEY. If the binary is not a PSI type, an error is returned',
                        action='store')
    parser.add_argument('--psi-signed-len', metavar='LEN',
                        help='final signed lenth of the PSI including pad and signature',
                        action='store')
    parser.add_argument('--secpack', metavar='MASTER_KEY',
                        help='sign the SecPack with MASTER_KEY. If --psi is also specified, that signature will be applied first',
                        action='store')
    parser.add_argument('--dev-sign', help='use the devkey signature slot in the SecPack; otherwise, use production slot',
                        action='store_const', const=True, default=False)
    parser.add_argument('--bswap-secpack-hash', help='format SecPack hash such that each 32 bit word is byte-swapped',
                        action='store_const', const=True, default=False)
    parser.add_argument('--sign-exec', metavar='EXEC',
                        help='executable to use for creating signature',
                        action='store', required=True)
    parser.add_argument('--verbose', help='print lots of operational info',
                        action='store_const', const=True, default=False)
    parser.add_argument('--debug-preserve-tmp', help='do not delete the expanded FLS temp directory',
                        action='store_const', const=True, default=False)
    parser.add_argument('src', metavar='IN_FLS', help='FLS to (re-)sign',
                               action='store')
    parser.add_argument('dest', metavar='OUT_FLS', help='FLS with signed values',
                               action='store')
    parser.parse_args(argv, namespace=options)

    if not options.psi and not options.secpack:
        print("*** Error: must specify at least one of --psi and --secpack")
        exit(-1)
    if options.psi and not options.psi_signed_len:
        print("*** Error: must specify --psi-signed-len with --psi")
        exit(-1)

    the_fls = fls.new(options.src, options.bswap_secpack_hash, options.verbose, options.debug_preserve_tmp)

    if options.psi:
        gold_key_path = options.psi
        if not os.path.isfile(gold_key_path):
            print("*** Error: {} (GOLD_KEY) does not exist.".format(options.psi))
            exit(-1)

        the_psi = the_fls.psi(int(options.psi_signed_len, 0))
        tbs_data = the_psi.tbs_data()
        sig = do_signature(tbs_data, gold_key_path, little_endian_sig=True)
        the_psi.inject_signature(sig)
        # not strictly necessary
        the_psi.save()

    if options.secpack:
        master_key_path = options.secpack
        if not os.path.isfile(master_key_path):
            print("*** Error: {} (MASTER_KEY) does not exist.".format(options.secpack))
            exit(-1)

        the_secpack = the_fls.secpack()
        the_secpack.set_timestamp()
        tbs_data = the_secpack.tbs_data()
        sig = do_signature(tbs_data, master_key_path, goofy_hash=options.bswap_secpack_hash, little_endian_sig=not options.bswap_secpack_hash)
        the_secpack.inject_signature(sig, options.dev_sign)

        the_secpack.save()

    # repack FLS
    the_fls.pack_fls(options.dest)


if __name__ == '__main__':
    main(sys.argv[1:])