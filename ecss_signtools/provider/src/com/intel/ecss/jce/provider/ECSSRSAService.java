/**
 *
 */
package com.intel.ecss.jce.provider;

import java.security.Provider;
import org.bouncycastle.asn1.pkcs.PKCSObjectIdentifiers;

/**
 * @author mdwood
 *
 */
class ECSSRSAService extends Provider.Service {

	/**
	 */
	public ECSSRSAService(Provider provider, String type, String algorithm, String className) {
		super(provider, type, algorithm, className, null, null);
	}

	@Override
	public boolean supportsParameter(Object obj) {
		//System.err.println(getClass().getName() + " supportsParameter");
		if (obj instanceof ECSSRSAPrivateKey) {
			return true;
		}

		return false;
	}

}
