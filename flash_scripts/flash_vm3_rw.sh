# Copyright (C) 2024 Intel Corporation
# Author: Chen, Gang G <gang.g.chen@intel.com>
# SPDX-License-Identifier: BSD-3-Clause

#!/bin/sh
# the script will format vm3 RW partition and flash GPT table to it

usage()
{
	echo $1
	echo "Usage: $0 <vm3_rw.img>"
}

if [ $# != 1 ]; then
	usage "Invalid arguments"
	exit 1
fi

VM3_RW_IMG=$(readlink -f $1)

echo "You are going to create image ($VM3_RW_IMG ) for VM3"
echo "Please confirm that output image paths are correct !"
read -p "Continue ? [y/n]" yn
case $yn in
	[Yy]*) ;;
	[Nn]*) exit;;
esac

mkfs.ext4 $VM3_RW_IMG -F

TEMP_DIR=$(mktemp -d)
TEMP_INI=$(mktemp)

rm -rf ${TEMP_DIR}/*
cp gpt.ini $TEMP_INI
sed -e '/partitions =/s/bootloader //g' -e '/partitions =/s/boot //g' -e '/partitions =/s/misc //g' -i $TEMP_INI
sed -e '/partitions =/s/acpio //g' -e '/partitions =/s/super //g' -e '/partitions =/s/vbmeta //g' -i $TEMP_INI
sed -e 's/partitions += vendor_boot//' -i $TEMP_INI
sed -e 's/partitions += config//' -i $TEMP_INI

SIZE_GB=$(fdisk -l $VM3_RW_IMG | grep Disk | awk '{print $3}')
SIZE_GB=$(awk "BEGIN {print int($SIZE_GB)}")
python3 ./gpt_ini2bin.py $TEMP_INI > ${TEMP_DIR}/gpt.bin
python3 ./create_gpt_image.py --create $VM3_RW_IMG --size=${SIZE_GB}G --flashfiles $TEMP_DIR

sync
