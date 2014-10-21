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
public final class IntelECSSProvider extends Provider {

	/**
	 */
	public IntelECSSProvider() {
		super("IntelECSS", 1.0, "Abstraction of Intel(R) IT Enterprise Code Signing System");

		putService(new ECSSRSAService(this, "Signature", "SHA1withRSA", "com.intel.ecss.jce.provider.SHA1withRSA"));
		putService(new ECSSRSAService(this, "Signature", "SHA256withRSA", "com.intel.ecss.jce.provider.SHA256withRSA"));
		putService(new Service(this, "KeyFactory", "RSA", "com.intel.ecss.jce.provider.RSAKeyFactory", null, null));
		putService(new Service(this, "KeyFactory", PKCSObjectIdentifiers.rsaEncryption.getId(), "com.intel.ecss.jce.provider.RSAKeyFactory", null, null));
	}

}
