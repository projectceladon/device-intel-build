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

package com.android.verity;

import java.security.PrivateKey;
import java.security.Security;
import org.bouncycastle.jce.provider.BouncyCastleProvider;

public class VeritySigner {

    // USAGE:
    //     VeritySigner <contentfile> <key.pem> <sigfile>
    // To verify that this has correct output:
    //     openssl rsautl -raw -inkey <key.pem> -encrypt -in <sigfile> > /tmp/dump
    public static void main(String[] args) throws Exception {
        // Start Intel addition to enable specifying a provider class using
        // the same parameter form as signapk. The style is copied directly
        // from original version at system/extras/verity/BootSignature.java.
        Security.addProvider(new BouncyCastleProvider());
        int argStart = 0;
        if (args[0].equals("-providerClass")) {
            Utils.loadProviderIfNecessary(args[1]);
            argStart += 2;
        }
        byte[] content = Utils.read(args[argStart+0]);
        PrivateKey privateKey = Utils.loadPEMPrivateKey(Utils.read(args[argStart+1]));
        byte[] signature = Utils.sign(privateKey, content);
        Utils.write(signature, args[argStart+2]);
        // End of Intel changes
    }
}
