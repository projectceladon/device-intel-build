/**
 *
 */
package com.intel.ecss.jce.provider;

import java.lang.Thread;

import java.io.UnsupportedEncodingException;
import java.io.ByteArrayInputStream;
import java.io.IOException;

import java.security.InvalidKeyException;
import java.security.Key;
import java.security.KeyFactory;
import java.security.KeyFactorySpi;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.spec.InvalidKeySpecException;
import java.security.spec.KeySpec;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.NoSuchAlgorithmException;

import org.bouncycastle.asn1.ASN1InputStream;
import org.bouncycastle.asn1.ASN1Encodable;
import org.bouncycastle.asn1.DEROctetString;
import org.bouncycastle.asn1.pkcs.PrivateKeyInfo;
import org.bouncycastle.asn1.pkcs.PKCSObjectIdentifiers;

import org.bouncycastle.jce.provider.BouncyCastleProvider;

/**
 * @author mdwood
 *
 */
public final class RSAKeyFactory extends KeyFactorySpi {

	/**
	 *
	 */
	public RSAKeyFactory() {
	}

	/* (non-Javadoc)
	 * @see java.security.KeyFactorySpi#engineGeneratePrivate(java.security.spec.KeySpec)
	 */
	@Override
	protected PrivateKey engineGeneratePrivate(KeySpec spec)
			throws InvalidKeySpecException {
		//System.err.println(getClass().getName() + " engineGeneratePrivate");
		if (!(spec instanceof PKCS8EncodedKeySpec)) {
			throw new InvalidKeySpecException();
		}
		PKCS8EncodedKeySpec pkcs8Spec = (PKCS8EncodedKeySpec)spec;
		String keyName;
		try {
			ASN1InputStream asn1is = new ASN1InputStream(new ByteArrayInputStream(pkcs8Spec.getEncoded()));
			PrivateKeyInfo pki = PrivateKeyInfo.getInstance(asn1is.readObject());
			if (!pki.getPrivateKeyAlgorithm().getAlgorithm().equals(PKCSObjectIdentifiers.rsaEncryption)) {
				throw new InvalidKeySpecException("Algorithm not supported");
			}

			DEROctetString privKey = (DEROctetString)pki.parsePrivateKey();
			keyName = new String(privKey.getOctets(), "UTF-8");
			if (!keyName.startsWith("ECSS! ")) {
				throw new InvalidKeySpecException("PKCS #8 content not an ECSS reference");
			}
		}
		catch (UnsupportedEncodingException e) {
			throw new InvalidKeySpecException("Key name is not a UTF-8 string");
		}
		catch (IOException e) {
			throw new InvalidKeySpecException("Data too short");
		}

		return new ECSSRSAPrivateKey(keyName);
	}

	/* (non-Javadoc)
	 * @see java.security.KeyFactorySpi#engineGeneratePublic(java.security.spec.KeySpec)
	 */
	@Override
	protected PublicKey engineGeneratePublic(KeySpec spec)
			throws InvalidKeySpecException {
		// No public key implementation in this provider, so proxy to BouncyCastle.
		KeyFactory bckf;
		try {
			bckf = KeyFactory.getInstance("RSA", new BouncyCastleProvider());
		}
		catch (NoSuchAlgorithmException e) {
			throw new InvalidKeySpecException(e.getMessage());
		}
		return bckf.generatePublic(spec);
	}

	/* (non-Javadoc)
	 * @see java.security.KeyFactorySpi#engineGetKeySpec(java.security.Key, java.lang.Class)
	 */
	@Override
	protected <T extends KeySpec> T engineGetKeySpec(Key arg0, Class<T> arg1)
			throws InvalidKeySpecException {
		System.err.println(getClass().getName() + " engineGetKeySpec");
		return null;
	}

	/* (non-Javadoc)
	 * @see java.security.KeyFactorySpi#engineTranslateKey(java.security.Key)
	 */
	@Override
	protected Key engineTranslateKey(Key arg0) throws InvalidKeyException {
		System.err.println(getClass().getName() + " engineTranslateKey");
		return null;
	}

}
