package com.android.signapk;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.FileReader;
import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.LinkedList;
import java.util.List;
import java.util.Iterator;

class SignApk {

    private static void usage() {
        System.err.println("Usage: signapk [-w] " +
                           "publickey.x509[.pem] certnamefile" +
                           "input.jar output.jar");
        System.err.println("\twhere certnamefile is a file with the " +
                           "\tcertificate name in it");
        System.exit(2);
    }


    private static void copyFile(String inputFilename, String outputFilename) throws FileNotFoundException, IOException {
        File inputFile = new File(inputFilename);
        if (!inputFile.exists()) {
            throw new FileNotFoundException();
        }
        FileInputStream inputStream = new FileInputStream(inputFile);
        FileOutputStream outputStream = new FileOutputStream(new File(outputFilename));
        int bytesRed = 0;
        final int BUF_SIZE = 4096;
        byte buf[] = new byte[BUF_SIZE];

        while (bytesRed != -1) {
            bytesRed = inputStream.read(buf);
            switch (bytesRed) {
            case BUF_SIZE:
                outputStream.write(buf);
                break;

            case -1:
                break;

            default:
                for (int i= 0; i < bytesRed; i++) {
                    outputStream.write(buf[i]);
                }
                break;
            }
        }
        inputStream.close();
        outputStream.close();

    }

    private static Boolean signFile(String inputFilename, String outputFilename,
                                    String certName, Boolean ota)
 {
        try {
            copyFile(inputFilename, outputFilename);
        } catch (FileNotFoundException e) {
            System.err.println("Input file not found: " + inputFilename);
            return false;
        } catch (IOException e) {
            System.err.println("Could not copy " + inputFilename +
                               " to " + outputFilename);
            System.err.println(e.getMessage());
            return false;
        }

        File signFileDir = new File(System.getenv("SIGNFILE_PATH"));
        File signFile = new File(signFileDir, "SignFile");

        List<String> commandLine = new LinkedList<String>();
        commandLine.add(signFile.toString());
        commandLine.add("-ts");
        commandLine.add("-c");
        commandLine.add(certName);
        if (ota) {
            commandLine.add("-ota");
        }
        commandLine.add(outputFilename);

        System.out.print("    redirecting: ");
        Iterator<String> iterator = commandLine.iterator();
        while (iterator.hasNext()) {
            System.out.print(iterator.next());
            System.out.print(" ");
        }
        System.out.println("");

        ProcessBuilder pb = new ProcessBuilder(commandLine);
        pb.redirectErrorStream(true);
        pb.directory(signFileDir);
        try {
            Process process = pb.start();
            InputStream outStream = process.getInputStream();
            int status = process.waitFor();
            BufferedReader in = new BufferedReader(new InputStreamReader(outStream));
            BufferedReader errin = new BufferedReader(new InputStreamReader(outStream));
            while (in.ready()) {
                System.err.println(in.readLine());
            }
            while (errin.ready()) {
                System.err.println(errin.readLine());
            }
            if (status != 0) {
                System.err.println("SignFile failed: " + status);
                return false;
            }
        } catch (IOException e) {
            System.err.println("Something went wrong in starting process or " +
                               "reading from it");
            return false;
        } catch (java.lang.InterruptedException e) {
	    Thread.currentThread().interrupt();
            System.err.println("Something went wrong in starting process");
            return false;
        }
        return true;
    }

    private static String getCertName(String certFilename) {
        File certFile = new File(certFilename);
        String certName = "";
        try {
            BufferedReader reader = new BufferedReader(new FileReader(certFilename));
            certName = reader.readLine();
            reader.close();
        } catch (FileNotFoundException e) {
            System.err.println("File not found: " + certFilename);
            System.exit(3);
        } catch (IOException e) {
            System.err.println("Could not read file: " + certFilename);
            System.exit(4);
        }
        return certName;
    }

    public static void main(String[] args) {
        if (args.length < 4) usage();

        boolean signWholeFile = false;
        int argstart = 0;
        if (args[0].equals("-w")) {
            signWholeFile = true;
            argstart = 1;
        }

        if ((args.length - argstart) % 2 == 1) usage();
        int numKeys = ((args.length - argstart) / 2) - 1;
        if (signWholeFile && numKeys > 1) {
            System.err.println("Only one key may be used with -w.");
            System.exit(2);
        }
        if (numKeys > 1) {
            System.err.println("Hardware signing tool only supports signing " +
                               "with one key.");
            System.exit(2);
        }

        String inputFilename = args[args.length-2];
        String outputFilename = args[args.length-1];

        // the private key file is replaced with a file that contains
        // the certificate name in the signing server
        String certFilename = args[argstart+1];

        String certName = getCertName(certFilename);
        System.err.println("certName: " + certName);
        if (!signFile(inputFilename, outputFilename, certName, signWholeFile)) {
            System.exit(1);
        }
        System.exit(0);
    }
}
