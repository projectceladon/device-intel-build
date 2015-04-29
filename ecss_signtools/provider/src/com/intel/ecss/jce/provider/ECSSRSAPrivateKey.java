/**
 *
 */
package com.intel.ecss.jce.provider;

import java.util.List;
import java.util.ArrayList;
import java.util.Arrays;
import java.math.BigInteger;
import java.security.PrivateKey;
import java.security.spec.InvalidKeySpecException;

/**
 * @author mdwood
 *
 */
public final class ECSSRSAPrivateKey implements PrivateKey {
	private List<String> params = null;

	public List<String> getKeyParams() {
		return params;
	}

	/**
	 *
	 */
	public ECSSRSAPrivateKey(String paramsString)
			throws InvalidKeySpecException {
		if (!paramsString.startsWith("ECSS! ")) {
			throw new InvalidKeySpecException("Key parameters are not an ECSS key reference");
		}

		params = new ArrayList<String>(Arrays.asList(paramsString.split("\\s+", 0)));
		params.remove(0);
	}

	/* (non-Javadoc)
	 * @see java.security.Key#getAlgorithm()
	 */
	@Override
	public String getAlgorithm() {
		//System.err.println(getClass().getName() + " getAlgorithm");
		return "RSA";
	}

	/* (non-Javadoc)
	 * @see java.security.Key#getEncoded()
	 */
	@Override
	public byte[] getEncoded() {
		System.err.println(getClass().getName() + " getEncoded");
		return null;
	}

	/* (non-Javadoc)
	 * @see java.security.Key#getFormat()
	 */
	@Override
	public String getFormat() {
		System.err.println(getClass().getName() + " getFormat");
		return null;
	}

}
