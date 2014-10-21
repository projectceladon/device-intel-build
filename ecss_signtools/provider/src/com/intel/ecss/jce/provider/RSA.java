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
import java.security.InvalidKeyException;
import java.security.InvalidParameterException;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.SignatureException;
import java.security.SignatureSpi;
import java.util.Collection;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;

import org.bouncycastle.cms.CMSException;
import org.bouncycastle.cms.CMSSignedData;
import org.bouncycastle.cms.SignerInformation;

/**
 * @author mdwood
 *
 */
class RSA extends SignatureSpi {

	private ECSSRSAPrivateKey key;
	private String hashType;
	private boolean signOp;
	private File contentTemp;
	private OutputStream contentTempStream;

	/**
	 *
	 */
	protected RSA(String alg) {
		super();

		if (alg == "SHA1withRSA") {
			hashType = "SHA1";
		}
		else if (alg == "SHA256withRSA") {
			hashType = "SHA256";
		}
		else {
			System.err.println("!!!!!!!!!! Subclass trying to use an algorithm I don't know! !!!!!!!!!!");
		}
		key = null;
		contentTemp = null;
		contentTempStream = null;
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
			contentTemp = File.createTempFile("content", "");
			contentTemp.deleteOnExit();
			contentTempStream =  new FileOutputStream(contentTemp);
		}
		catch (IOException e) {
			contentTemp = null;
			contentTempStream = null;
			throw new InvalidKeyException("Cannot create temporary signature content file");
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

		if (contentTempStream != null && signOp) {
			// Flush and close temp stream
			try {
				contentTempStream.flush();
				contentTempStream.close();

				File sigTemp = File.createTempFile("sig", "");
				sigTemp.deleteOnExit();

				// Call SignFile
				if (!RSA.signFile(contentTemp.getAbsolutePath(), sigTemp.getAbsolutePath(), key.getKeyParams(), hashType)) {
					throw new SignatureException("ECSS signing attempt failed");
				}

				// Read signature
				InputStream sigStream = new FileInputStream(sigTemp.getAbsolutePath());
				CMSSignedData sigBlock;
				try {
					sigBlock = new CMSSignedData(sigStream);
					Collection signers = sigBlock.getSignerInfos().getSigners();
					SignerInformation si = (SignerInformation)signers.iterator().next();
					sig = si.getSignature();
				} catch (CMSException e) {
					throw new SignatureException("Problem reading PKCS #7 signature block from ECSS");
				}
			} catch (IOException e) {
				throw new SignatureException("Error handling temporary files");
			}
		}
		else {
			throw new SignatureException("Signature not initialized or initialized for verify");
		}

		// Clear state
		key = null;
		hashType = null;
		contentTemp = null;

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
		if (contentTempStream != null) {
			try {
				contentTempStream.write(arg0);
			} catch (IOException e) {
				throw new SignatureException("Unable to write temporary file");
			}
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
		if (contentTempStream != null) {
			try {
				contentTempStream.write(arg0, arg1, arg2);
			} catch (IOException e) {
				throw new SignatureException("Unable to write temporary file");
			}
		}
		else {
			throw new SignatureException("Signature not initialized");
		}

	}

	private static Boolean signFile(
			String inputFilename,
			String outputFilename,
			List<String> signParams,
			String hashType) throws SignatureException {
		if (System.getenv("SIGNFILE_PATH") == null) {
			throw new SignatureException("Must set SIGNFILE_PATH environment variable");
		}
		File signFileDir = new File(System.getenv("SIGNFILE_PATH"));
		File signFile = new File(signFileDir, "SignFile");

		List<String> commandLine = new LinkedList<String>();
		commandLine.add(signFile.getAbsolutePath());
		commandLine.add("-vv");
		commandLine.add("-s"); commandLine.add("cl");				// detached signature
		commandLine.add("-ts");										// disable timestamping protocol
		commandLine.add("-ha"); commandLine.add(hashType);			// hash type to use
		commandLine.add("-cf"); commandLine.add(outputFilename);	// detached signature result
		commandLine.addAll(signParams);								// ECSS certificate name and other params
		commandLine.add(inputFilename);

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
			BufferedReader stderr = new BufferedReader(new InputStreamReader(process.getErrorStream()));
			while (stdout.ready()) {
				System.err.println(stdout.readLine());
			}
			while (stderr.ready()) {
				System.err.println(stderr.readLine());
			}
			if (status != 0) {
				System.err.println("SignFile failed: " + status);
				return false;
			}
		} catch (IOException e) {
			System.err.println("Something went wrong in starting process or "
					+ "reading from it");
			return false;
		} catch (java.lang.InterruptedException e) {
			Thread.currentThread().interrupt();
			System.err.println("Something went wrong in starting process");
			return false;
		}
		return true;
	}
}
