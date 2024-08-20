# Copyright (C) 2024 Intel Corporation
# Author: Chen, Gang G <gang.g.chen@intel.com>
# SPDX-License-Identifier: BSD-3-Clause

#!/bin/sh

usage()
{
	echo $1
	echo "Usage: $0 <flashfiles>.zip <vm3_ro.img> <vm3_rw.img>"
}

if [ $# != 3 ]; then
	usage "Invalid arguments"
	exit 1
fi

ZIP_FILE=$(readlink -f $1)
VM_RO_IMG=$(readlink -f $2)
VM3_RW_IMG=$(readlink -f $3)

if [ ! -f $ZIP_FILE ]; then
	usage "$ZIP_FILE not exist"
	exit 1
fi

echo "You are going to create image ($VM_RO_IMG) for VM1 and image($VM3_RW_IMG ) for VM3"
echo "Please confirm that output image paths are correct !"
read -p "Continue ? [y/n]" yn
case $yn in
	[Yy]*) ;;
	[Nn]*) exit;;
esac

mkfs.ext4 $VM_RO_IMG -F
mkfs.ext4 $VM3_RW_IMG -F
TEMP_DIR=$(mktemp -d)
pushd $TEMP_DIR
7z x $ZIP_FILE
simg2img super.img super.img.raw
mv super.img.raw super.img
simg2img config.img config.img.raw
mv config.img.raw config.img
popd

GPT_INI=/home/root/android-flashtool/gpt.ini
if [ -f $TEMP_DIR/gpt.ini ]; then
	GPT_INI=$TEMP_DIR/gpt.ini
	echo "Use gpt.ini in flashfiles: $GPT_INI"
elif [ -f $GPT_INI ]; then
	echo "Use default gpt.ini: $GPT_INI"
else
	echo "No gpt.ini found! exit!"
	exit 0
fi

TEMP_INI=$(mktemp)
sed -e '/partitions =/s/teedata //g' $GPT_INI >$TEMP_INI
sed -e '/partitions =/s/share_data//g' -e '/partitions =/s/metadata //g' -e '/partitions =/s/persistent //g' -e '/partitions =/s/data //g' -i $TEMP_INI
SIZE_GB=$(fdisk -l $VM_RO_IMG | grep Disk | awk '{print $3}')
SIZE_GB=$(awk "BEGIN {print int($SIZE_GB)}")
python3 ./gpt_ini2bin.py $TEMP_INI > ${TEMP_DIR}/gpt.bin
python3 ./create_gpt_image.py --create $VM_RO_IMG --size=${SIZE_GB}G --flashfiles $TEMP_DIR

cp $GPT_INI $TEMP_INI
sed -e '/partitions =/s/bootloader //g' -e '/partitions =/s/boot //g' -e '/partitions =/s/misc //g' -i $TEMP_INI
sed -e '/partitions =/s/acpio //g' -e '/partitions =/s/super //g' -e '/partitions =/s/vbmeta //g' -i $TEMP_INI
sed -e 's/partitions += vendor_boot//' -i $TEMP_INI
sed -e 's/partitions += config//' -i $TEMP_INI

SIZE_GB=$(fdisk -l $VM3_RW_IMG | grep Disk | awk '{print $3}')
SIZE_GB=$(awk "BEGIN {print int($SIZE_GB)}")
python3 ./gpt_ini2bin.py $TEMP_INI > ${TEMP_DIR}/gpt.bin
python3 ./create_gpt_image.py --create $VM3_RW_IMG --size=${SIZE_GB}G --flashfiles $TEMP_DIR

rm -rf ${TEMP_DIR}/*
sync
