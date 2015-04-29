package com.intel.ecss.jce.provider;

import java.io.File;
import java.security.ProviderException;

class IntelECSSProviderParams {
	static final String SIGNFILE_PATH_ENV = "SIGNFILE_PATH";
	static final String SIGNFILE_BIN = "SignFile";
	static final int MAX_SIGNATURE_SIZE = 4096;


	static void checkEnvironmentConfiguration() {
		String signfilePathEnv = System.getenv(IntelECSSProviderParams.SIGNFILE_PATH_ENV);
		if (signfilePathEnv == null) {
			throw new ProviderException("Must set SIGNFILE_PATH environment variable");
		}
		File signfilePath = new File(signfilePathEnv);
		File signfileExe = new File(signfilePath, IntelECSSProviderParams.SIGNFILE_BIN);
		if (!signfileExe.exists() || !signfileExe.canExecute()) {
			throw new ProviderException("File " + signfileExe.getAbsolutePath() + " does not exist or is not executable");
		}
	}
}
