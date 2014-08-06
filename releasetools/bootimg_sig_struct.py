import binascii

from pyasn1.type import univ, namedtype, char
from pyasn1.codec.der import encoder as der_encoder
from pyasn1_modules import rfc2459 as x509
from pyasn1_modules import rfc2437 as pkcs1

# ==========================================================================
# From Google verified boot design doc (pseudo ASN.1)
# ==========================================================================
#
# AndroidVerifiedBootSignature DEFINITIONS ::=
#   BEGIN
#       FormatVersion ::= INTEGER
#       AlgorithmIdentifier ::= SEQUENCE {
#           algorithm OBJECT IDENTIFIER,
#           parameters ANY DEFINED BY algorithm OPTIONAL
#       }
#       AuthenticatedAttributes ::= SEQUENCE {
#           target CHARACTER STRING,
#           length INTEGER
#       }
#       Signature ::= OCTET STRING
#   END
#
# AndroidVerifiedBootKeystore DEFINITIONS ::=
#   BEGIN
#       FormatVersion ::= INTEGER
#       KeyBag ::= SEQUENCE {
#           Key ::= SEQUENCE {
#               AlgorithmIdentifier ::= SEQUENCE {
#                   algorithm OBJECT IDENTIFIER,
#                   parameters ANY DEFINED BY algorithm OPTIONAL
#               }
#               KeyMaterial ::= RSAPublicKey
#           }
#       }
#       Signature ::= AndroidVerifiedBootSignature
#   END
#
# ==========================================================================
# As Implemented and Confirmed Against L Source (valid ASN.1)
# ==========================================================================
#
# AndroidVerifiedBoot DEFINITIONS ::= BEGIN
#   -- From PKCS #1/RFC3279 ASN.1 module
#   RSAPublicKey ::= SEQUENCE {
#       modulus           INTEGER,  -- n
#       publicExponent    INTEGER   -- e
#   }
#
#   AlgorithmIdentifier ::= SEQUENCE {
#       algorithm OBJECT IDENTIFIER,
#       parameters ANY DEFINED BY algorithm OPTIONAL
#   }
#
#   AuthenticatedAttributes ::= SEQUENCE {
#       target PrintableString,  -- specific version of CHARACTER STRING accepted by a compiler
#       length INTEGER
#   }
#
#   AndroidVerifiedBootSignature ::= SEQUENCE {
#       formatVersion INTEGER,
#       algorithmId AlgorithmIdentifier,
#       attributes AuthenticatedAttributes,
#       signature OCTET STRING
#   }
#
#   KeyBag ::= SEQUENCE OF KeyInfo
#
#   KeyInfo ::= SEQUENCE {
#       algorithm AlgorithmIdentifier,
#       keyMaterial RSAPublicKey
#   }
#
#   InnerKeystore ::= SEQUENCE {
#       formatVersion INTEGER,
#       bag KeyBag
#   }
#
#   AndroidVerifiedBootKeystore ::= SEQUENCE {
#       formatVersion INTEGER,
#       bag KeyBag,
#       signature AndroidVerifiedBootSignature
#   }
# END

sha1WithRSAEncryptionOID = univ.ObjectIdentifier((1, 2, 840, 113549, 1, 1, 5))
sha256WithRSAEncryptionOID = univ.ObjectIdentifier((1, 2, 840, 113549, 1, 1, 11))


class AuthenticatedAttributes(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('target', char.PrintableString()),
        namedtype.NamedType('length', univ.Integer())
    )


class AndroidVerifiedBootSignature(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('formatVersion', univ.Integer()),
        namedtype.NamedType('algorithmId', x509.AlgorithmIdentifier()),
        namedtype.NamedType('attributes', AuthenticatedAttributes()),
        namedtype.NamedType('signature', univ.OctetString())
    )


class KeyInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('algorithm', x509.AlgorithmIdentifier()),
        namedtype.NamedType('keyMaterial', pkcs1.RSAPublicKey())
    )

class KeyBag(univ.SequenceOf):
    componentType = KeyInfo()


class InnerKeystore(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('formatVersion', univ.Integer()),
        namedtype.NamedType('bag', KeyBag()),
    )


class AndroidVerifiedBootKeystore(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('formatVersion', univ.Integer()),
        namedtype.NamedType('bag', KeyBag()),
        namedtype.NamedType('signature', AndroidVerifiedBootSignature())
    )


# if run as main, build a sample of each structure a smoke test
def main():
    attributes = AuthenticatedAttributes()
    attributes.setComponentByName("target", "test")
    attributes.setComponentByName("length", 1024)
    data = der_encoder.encode(attributes)
    print "attributes " + binascii.hexlify(data)

    ident = x509.AlgorithmIdentifier()
    ident.setComponentByName("algorithm", sha256WithRSAEncryptionOID)
    data = der_encoder.encode(ident)
    print "ident " + binascii.hexlify(data)

    sig = AndroidVerifiedBootSignature()
    sig.setComponentByName('formatVersion', 1)
    sig.setComponentByName('algorithmId', ident)
    sig.setComponentByName('attributes', attributes)
    sig.setComponentByName('signature', univ.OctetString('abcdef0123456789'))
    data = der_encoder.encode(sig)
    print "sig " + binascii.hexlify(data)

    material = pkcs1.RSAPublicKey()
    material.setComponentByName('modulus', 'abc123')
    material.setComponentByName('publicExponent', (1 << 16) + 1)

    keyinfo = KeyInfo()
    keyinfo.setComponentByName('algorithm', ident)
    keyinfo.setComponentByName('keyMaterial', material)

    bag = KeyBag()
    bag.setComponentByPosition(0, keyinfo)

    keystore = AndroidVerifiedBootKeystore()
    keystore.setComponentByName('formatVersion', 1)
    keystore.setComponentByName('bag', bag)
    keystore.setComponentByName('signature', sig)


if __name__ == "__main__":
    main()
