package com.intel.ecss.apps;

import org.bouncycastle.asn1.DEROutputStream;
import org.bouncycastle.asn1.DEROctetString;
import org.bouncycastle.asn1.pkcs.PrivateKeyInfo;
import org.bouncycastle.asn1.pkcs.PKCSObjectIdentifiers;
import org.bouncycastle.asn1.x509.AlgorithmIdentifier;
import org.bouncycastle.operator.DefaultSignatureAlgorithmIdentifierFinder;
import java.nio.charset.Charset;
import java.io.File;
import java.io.FileOutputStream;
import java.io.ByteArrayOutputStream;
import java.io.PrintWriter;
import java.io.IOException;
import org.bouncycastle.util.encoders.Base64;

class MakePk8 {
    public static final String DER_FILE_EXTENSION = ".pk8";
    public static final String PEM_FILE_EXTENSION = ".pem";

    public static void usage() {
        System.err.println("Usage: makepk8 " +
                           "[-pem] " +
                           "<keyfile-base> " +
                           "<algorithm> " +
                           "<SignFile-params>");
        System.exit(2);
    }

    public static void main(String[] args) {
        boolean savePem = false;
        String keyfileBasePath;
        String algorithm;
        String signfileParams;

        int argstart = 0;
        while (argstart < args.length && args[argstart].startsWith("-")) {
            if ("-pem".equals(args[argstart])) {
                savePem = true;
                ++argstart;
            } else {
                usage();
            }
        }
        if ((args.length - argstart) != 3) {
            usage();
        }
        keyfileBasePath = args[argstart];
        algorithm = args[argstart + 1];
        signfileParams = args[argstart + 2];

        AlgorithmIdentifier algId = null;
        if (algorithm.equals("RSA")) {
            algId =
                new AlgorithmIdentifier(PKCSObjectIdentifiers.rsaEncryption);
        }
        else {
            System.err.printf("Error: Unknown algorithm '%s'\n", algorithm);
            System.exit(1);
        }

        try {
            String privateKeyContent = "ECSS! " + signfileParams;
            PrivateKeyInfo priv = new PrivateKeyInfo(
                                    algId,
                                    new DEROctetString(
                                        privateKeyContent.getBytes(
                                            Charset.forName("UTF-8"))));
            File derFile = new File(keyfileBasePath + DER_FILE_EXTENSION);
            File pemFile = new File(keyfileBasePath + PEM_FILE_EXTENSION);

            ByteArrayOutputStream derMemoryStream = new ByteArrayOutputStream();
            DEROutputStream derEncoder = new DEROutputStream(derMemoryStream);
            derEncoder.writeObject(priv);
            derEncoder.flush();
            derEncoder.close();

            if (savePem) {
                FileOutputStream stream = new FileOutputStream(pemFile);
                PrintWriter writer = new PrintWriter(stream, true);

                writer.println("-----BEGIN PRIVATE KEY-----");
                byte[] encoded = Base64.encode(derMemoryStream.toByteArray());
                String encodedString = new String(encoded, "UTF-8");
                String[] lines = encodedString.split("(?<=\\G.{64})");
                for (int i = 0; i < lines.length; i++ ) {
                    writer.println(lines[i]);
                }
                writer.println("-----END PRIVATE KEY-----");
                writer.close();
            }

            FileOutputStream fileStream = new FileOutputStream(derFile);
            fileStream.write(derMemoryStream.toByteArray());
            fileStream.flush();
            fileStream.close();
        }
        catch (IOException e) {
            System.err.printf("Error: IOException: %s\n", e.getMessage());
            System.exit(1);
        }
    }
}
