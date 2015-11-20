#!/bin/bash

# Copyright 2015 Intel Corporations
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Signer callout for sign_fls.py that uses the openssl command line to
# implement the actual signing operation.
#
# Current limitations:
# - Does not support private key files with passwords

function usage {
	echo "Usage $0 --sign-hash|--sign-data HASH_TYPE KEY_PATH DATA_PATH OUT_SIG_PATH"
	exit 1
}

OP=$1
HASH_TYPE=$2
KEY_PATH=$3
DATA_PATH=$4
OUT_SIG_PATH=$5

if [[ $# -ne 5 ]]; then
	echo "====> Invalid command: must have 5 parameters"
	usage
fi
if [[ $OP != "--sign-hash" && $OP != "--sign-data" ]]; then
	echo "====> First param must be --sign-hash or --sign-data"
	usage
fi
if [[ $HASH_TYPE != "SHA256" ]]; then
	echo "====> HASH_TYPE must be SHA256"
	usage
fi
if [[ ! -f $KEY_PATH || ! -f $DATA_PATH ]]; then
	echo "====> KEY_PATH or DATA_PATH does not exist"
	usage
fi

# Compute the hash if necessary
if [[ $OP == "--sign-data" ]]; then
	TMP=$(mktemp)
	trap 'rm "$TMP"' EXIT

	# Compute the raw hash. Openssl algorithm selectors match script params.
	openssl $HASH_TYPE -binary -out $TMP $DATA_PATH
	DATA_PATH=$TMP
fi

# Compute the signature value
if [[ $KEY_PATH != *.pem ]]; then
	KEYFORM='-keyform DER'
fi
openssl pkeyutl -sign -in $DATA_PATH $KEYFORM -inkey $KEY_PATH -out $OUT_SIG_PATH -pkeyopt digest:$HASH_TYPE