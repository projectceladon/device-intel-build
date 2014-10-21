/*
 * Copyright (C) 2013 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>

/* HACK: we need the RSAPublicKey struct
 * but RSA_verify conflits with openssl */
#define RSA_verify RSA_verify_mincrypt
#include "mincrypt/rsa.h"
#undef RSA_verify

#include <openssl/evp.h>
#include <openssl/objects.h>
#include <openssl/pem.h>
#include <openssl/rsa.h>
#include <openssl/sha.h>
#include <openssl/x509.h>

// Convert OpenSSL RSA private key to android pre-computed RSAPublicKey format.
// Lifted from secure adb's mincrypt key generation.
static int convert_to_mincrypt_format(RSA *rsa, RSAPublicKey *pkey)
{
    int ret = -1;
    unsigned int i;

    if (RSA_size(rsa) != RSANUMBYTES)
        goto out;

    BN_CTX* ctx = BN_CTX_new();
    BIGNUM* r32 = BN_new();
    BIGNUM* rr = BN_new();
    BIGNUM* r = BN_new();
    BIGNUM* rem = BN_new();
    BIGNUM* n = BN_new();
    BIGNUM* n0inv = BN_new();

    BN_set_bit(r32, 32);
    BN_copy(n, rsa->n);
    BN_set_bit(r, RSANUMWORDS * 32);
    BN_mod_sqr(rr, r, n, ctx);
    BN_div(NULL, rem, n, r32, ctx);
    BN_mod_inverse(n0inv, rem, r32, ctx);

    pkey->len = RSANUMWORDS;
    pkey->n0inv = 0 - BN_get_word(n0inv);
    for (i = 0; i < RSANUMWORDS; i++) {
        BN_div(rr, rem, rr, r32, ctx);
        pkey->rr[i] = BN_get_word(rem);
        BN_div(n, rem, n, r32, ctx);
        pkey->n[i] = BN_get_word(rem);
    }
    pkey->exponent = BN_get_word(rsa->e);

    ret = 0;

    BN_free(n0inv);
    BN_free(n);
    BN_free(rem);
    BN_free(r);
    BN_free(rr);
    BN_free(r32);
    BN_CTX_free(ctx);

out:
    return ret;
}

static int write_public_keyfile(RSA *private_key, const char *key_path)
{
    RSAPublicKey pkey;
    BIO *bfile = NULL;
    int ret = -1;

    if (convert_to_mincrypt_format(private_key, &pkey) < 0)
        goto out;

    bfile = BIO_new_file(key_path, "w");
    if (!bfile)
        goto out;

    BIO_write(bfile, &pkey, sizeof(pkey));
    BIO_flush(bfile);

    ret = 0;
out:
    BIO_free_all(bfile);
    return ret;
}

static int convert_key(const char *certfile, const char *keyfile)
{
    int ret = -1;
    FILE *f = NULL;
    X509 *cert = NULL;
    RSA* rsa = NULL;
//    BIGNUM* exponent = BN_new();
    EVP_PKEY* pkey = NULL;

    f = fopen(certfile, "r");
    if (!f) {
        printf("Failed to open '%s'\n", certfile);
        goto out;
    }

    if (!PEM_read_X509(f, &cert, NULL, NULL)) {
        printf("Failed to read certificate.\n");
        goto out;
    }

    pkey = X509_get_pubkey(cert);
    if (!pkey) {
        printf("Failed to get public key\n");
        goto out;
    }

    rsa = EVP_PKEY_get1_RSA(pkey);
    if (!rsa) {
        printf("Failed to get RSA public key\n");
        goto out;
    }

    if (write_public_keyfile(rsa, keyfile) < 0) {
        printf("Failed to write public key\n");
        goto out;
    }

    ret = 0;

out:
    if (f)
        fclose(f);
    X509_free(cert);
    EVP_PKEY_free(pkey);
    RSA_free(rsa);
//    BN_free(exponent);
    return ret;
}

static void usage(){
    printf("Usage: cert_to_verity_public <path-to-cert> <path-to-key>");
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        usage();
        exit(-1);
    }
    return convert_key(argv[1], argv[2]);
}
