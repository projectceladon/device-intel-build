/**
 *
 */
package com.intel.ecss.jce.provider;

import java.io.BufferedOutputStream;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.io.FileNotFoundException;
import java.security.InvalidKeyException;
import java.security.InvalidParameterException;
import java.security.NoSuchAlgorithmException;
import java.security.ProviderException;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.SignatureException;
import java.security.SignatureSpi;
import java.security.MessageDigest;
import java.util.Collection;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.Arrays;

/**
 * @author mdwood
 *
 */
class RSA extends SignatureSpi {
	private ECSSRSAPrivateKey key;
	private String ecssHashType;
	private String ecssPadType;
	private String jcaHashType;
	private boolean signOp;
	private MessageDigest contentDigest;

	/**
	 *
	 */
	protected RSA(String alg) {
		super();

		if (alg == "SHA1withRSA") {
			ecssHashType = "SHA1";
			jcaHashType = "SHA-1";
			ecssPadType = "PKCS1";
		}
		else if (alg == "SHA256withRSA") {
			ecssHashType = "SHA256";
			jcaHashType = "SHA-256";
			ecssPadType = "PKCS1";
		}
		else {
			System.err.println("!!!!!!!!!! Subclass trying to use an algorithm I don't know! !!!!!!!!!!");
		}
	}

	/* (non-Javadoc)
	 * @see java.security.SignatureSpi#engineGetParameter(java.lang.String)
	 * @deprecated
	 * This method must be overridden because java.security.SignatureSpi is
	 * abstract, but @Deprecated annotation required to prevent compiler
	 * warnings about overriding deprecated methods.
	 */
	@Override
	@Deprecated
	protected Object engineGetParameter(String arg0)
			throws InvalidParameterException {
		System.err.println(getClass().getName() + " engineGetParameter");
		return null;
	}

	/* (non-Javadoc)
	 * @see java.security.SignatureSpi#engineSetParameter(java.lang.String, java.lang.Object)
	 * @deprecated
	 * This method must be overridden because java.security.SignatureSpi is
	 * abstract, but @Deprecated annotation required to prevent compiler
	 * warnings about overriding deprecated methods.
	 */
	@Override
	@Deprecated
	protected void engineSetParameter(String arg0, Object arg1)
			throws InvalidParameterException {
		System.err.println(getClass().getName() + " engineSetParameter");

	}

	/* (non-Javadoc)
	 * @see java.security.SignatureSpi#engineInitSign(java.security.PrivateKey)
	 */
	@Override
	protected void engineInitSign(PrivateKey signer) throws InvalidKeyException {
		//System.err.println(getClass().getName() + " engineInitSign");
		if (!(signer instanceof ECSSRSAPrivateKey)) {
			throw new InvalidKeyException("The key must be an ECSS RSA PrivateKey");
		}

		// Create temp file for content
		try {
			contentDigest = MessageDigest.getInstance(jcaHashType);
		}
		catch (NoSuchAlgorithmException e) {
			contentDigest = null;
			throw new ProviderException("Cannot create message digest instance");
		}

		key = (ECSSRSAPrivateKey)signer;
		signOp = true;
	}

	/* (non-Javadoc)
	 * @see java.security.SignatureSpi#engineSign()
	 */
	@Override
	protected byte[] engineSign() throws SignatureException {
		byte[] sig = null;

		if (contentDigest != null && signOp) {
			byte [] sigDigest = contentDigest.digest();

			sig = signFile(sigDigest);
		}
		else {
			throw new SignatureException("Signature not initialized or initialized for verify");
		}

		// Clear state
		key = null;
		contentDigest = null;

		return sig;
	}

	/* (non-Javadoc)
	 * @see java.security.SignatureSpi#engineInitVerify(java.security.PublicKey)
	 */
	@Override
	protected void engineInitVerify(PublicKey arg0) throws InvalidKeyException {
		System.err.println(getClass().getName() + " engineInitVerify");

		throw new InvalidKeyException("engineInitVerify not implemented");
	}

	/* (non-Javadoc)
	 * @see java.security.SignatureSpi#engineVerify(byte[])
	 */
	@Override
	protected boolean engineVerify(byte[] arg0) throws SignatureException {
		System.err.println(getClass().getName() + " engineVerify");
		return false;
	}

	/* (non-Javadoc)
	 * @see java.security.SignatureSpi#engineUpdate(byte)
	 */
	@Override
	protected void engineUpdate(byte arg0) throws SignatureException {
		if (contentDigest != null) {
			contentDigest.update(arg0);
		}
		else {
			throw new SignatureException("Signature not initialized");
		}
	}

	/* (non-Javadoc)
	 * @see java.security.SignatureSpi#engineUpdate(byte[], int, int)
	 */
	@Override
	protected void engineUpdate(byte[] arg0, int arg1, int arg2)
			throws SignatureException {
		if (contentDigest != null) {
			contentDigest.update(arg0, arg1, arg2);
		}
		else {
			throw new SignatureException("Signature not initialized");
		}

	}

	private byte[] signFile(
			byte[] sigDigest) throws SignatureException {

		IntelECSSProviderParams.checkEnvironmentConfiguration();

		File signFileDir = new File(System.getenv(IntelECSSProviderParams.SIGNFILE_PATH_ENV));
		File signFile = new File(signFileDir, IntelECSSProviderParams.SIGNFILE_BIN);
		File sigDigestTemp;
		File sigTemp;

		try {
			sigDigestTemp = File.createTempFile("content", "");
			sigDigestTemp.deleteOnExit();
			sigTemp = File.createTempFile("sig", "");
			sigTemp.deleteOnExit();

			FileOutputStream sigDigestStream = new FileOutputStream(sigDigestTemp.getAbsolutePath());
			sigDigestStream.write(sigDigest);
			sigDigestStream.close();
		} catch (FileNotFoundException e) {
			throw new SignatureException("File error creating temp files");
		} catch (IOException e) {
			throw new SignatureException("Error managing temp files");
		}

		List<String> commandLine = new LinkedList<String>();
		commandLine.add(signFile.getAbsolutePath());
		commandLine.add(sigDigestTemp.getAbsolutePath());
		commandLine.add("-vv");
		commandLine.add("-s"); commandLine.add("h");	// input is a computed hash
		commandLine.add("-ha"); commandLine.add(ecssHashType);	// hash type to use
		commandLine.add("-rsa_padding"); commandLine.add(ecssPadType); // RSA padding type
		commandLine.addAll(key.getKeyParams());	// ECSS certificate name and server params
		commandLine.add("-out"); commandLine.add(sigTemp.getAbsolutePath());

		StringBuilder redirectMsg = new StringBuilder("    redirecting: ");
		for (Iterator<String> iterator = commandLine.iterator();
			 iterator.hasNext();
			 redirectMsg.append(iterator.next()), redirectMsg.append(" "));
		System.err.println(redirectMsg);

		ProcessBuilder pb = new ProcessBuilder(commandLine);
		pb.redirectErrorStream(true);
		pb.directory(signFileDir);
		try {
			Process process = pb.start();
			int status = process.waitFor();
			BufferedReader stdout = new BufferedReader(new InputStreamReader(process.getInputStream()));
			while (stdout.ready()) {
				System.err.println(stdout.readLine());
			}
			if (status != 0) {
				throw new SignatureException("SignFile failed: " + status);
			}
		} catch (IOException e) {
			throw new SignatureException("Something went wrong in starting process or "
					+ "reading from it");
		} catch (java.lang.InterruptedException e) {
			Thread.currentThread().interrupt();
			throw new SignatureException("Something went wrong in starting process");
		}

		// Read signature
		/* The signature block has the following format:
		 * public key modulus : key length bytes (little-endian)
		 * public exponent : 4 bytes (little-endian)
		 * signature : key length bytes (little-endian)
		 */
		try {
			InputStream sigStream = new FileInputStream(sigTemp.getAbsolutePath());
			byte[] sigBytes = new byte[(IntelECSSProviderParams.MAX_SIGNATURE_SIZE / 8) * 2 + 4];
			int sigBytesLen = sigStream.read(sigBytes);
			if (((sigBytesLen - 4) % 128) != 0) {
				throw new SignatureException("Invalid signature result length. Must be a multiple of 1024 bits");
			}
			int sigLen = (sigBytesLen - 4) / 2;
			byte[] returnVal = new byte[sigLen];
			for (int i = 0; i < returnVal.length; i++) {
				returnVal[i] = sigBytes[sigBytesLen - 1 - i];
			}
			return returnVal;
		} catch (FileNotFoundException e) {
			throw new SignatureException("Signature block not written by SignFile");
		} catch (IOException e) {
			throw new SignatureException("Problem reading ECSS signature block");
		}
	}
}
