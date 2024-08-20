# Copyright (C) 2024 Intel Corporation
# Author: Chen, Gang G <gang.g.chen@intel.com>
# SPDX-License-Identifier: BSD-3-Clause

#!/bin/sh
# The script will format vm1 and vm2 rw partitions and flash GPT table to them

usage()
{
	echo $1
	echo "Usage: $0 <vm1_rw.img> <vm2_rw.img>"
}

if [ $# != 2 ]; then
	usage "Invalid arguments"
	exit 1
fi

VM1_RW_IMG=$(readlink -f $1)
VM2_RW_IMG=$(readlink -f $2)

echo "You are going to create two read-write images ($VM1_RW_IMG and $VM2_RW_IMG) for VM1 and VM2 separately"
echo "Please confirm that output image paths are correct !"
read -p "Continue ? [y/n]" yn
case $yn in
	[Yy]*) ;;
	[Nn]*) exit;;
esac

mkfs.ext4 $VM1_RW_IMG -F
mkfs.ext4 $VM2_RW_IMG -F


TEMP_DIR=$(mktemp -d)

TEMP_INI=$(mktemp)
rm -rf ${TEMP_DIR}/*
cp gpt.ini $TEMP_INI
sed -e '/partitions =/s/bootloader //g' -e '/partitions =/s/boot //g' -e '/partitions =/s/misc //g' -i $TEMP_INI
sed -e '/partitions =/s/acpio //g' -e '/partitions =/s/super //g' -e '/partitions =/s/vbmeta //g' -i $TEMP_INI
sed -e '/partitions =/s/share_data//g' -i $TEMP_INI #vm1/2 only
sed -e 's/partitions += vendor_boot//' -i $TEMP_INI
sed -e 's/partitions += config//' -i $TEMP_INI
sed -e 's/len = 128000/len = -1/' -i $TEMP_INI #vm1/2 only

SIZE_GB=$(fdisk -l $VM1_RW_IMG | grep Disk | awk '{print $3}')
SIZE_GB=$(awk "BEGIN {print int($SIZE_GB)}")
python3 ./gpt_ini2bin.py $TEMP_INI > ${TEMP_DIR}/gpt.bin
python3 ./create_gpt_image.py --create $VM1_RW_IMG --size=${SIZE_GB}G --flashfiles $TEMP_DIR

SIZE_GB=$(fdisk -l $VM2_RW_IMG | grep Disk | awk '{print $3}')
SIZE_GB=$(awk "BEGIN {print int($SIZE_GB)}")
python3 ./gpt_ini2bin.py $TEMP_INI > ${TEMP_DIR}/gpt.bin
python3 ./create_gpt_image.py --create $VM2_RW_IMG --size=${SIZE_GB}G --flashfiles $TEMP_DIR

sync
