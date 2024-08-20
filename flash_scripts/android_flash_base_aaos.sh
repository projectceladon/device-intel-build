# Copyright (C) 2024 Intel Corporation
# Author: Chen, Gang G <gang.g.chen@intel.com>
# SPDX-License-Identifier: BSD-3-Clause

#!/bin/sh

ZIP_FILE=$(readlink -f $1)
VM_IMG=$(readlink -f $2)
EXTRACT_DISK=/dev/nvme0n1p5

usage()
{
	echo $1
	echo "Usage: $0 <flashfiles>.zip <disk_name>"
	echo "disk_name can be partition(/dev/nvme0n1pX) or virtual_disk(/<path>/aaos.img)"
	echo "If you want to use virtual_disk(/home/root/aaos.img), please create it in advance"
	echo "For example: create a 400GB image. please make sure your disk has enough space"
	echo "command:  fallocate -l 400G /<path>/aaos.img"
}

if [ $# != 2 ]; then
	usage "Invalid arguments"
	exit 1
fi

if [ ! -f $ZIP_FILE ]; then
	usage "$ZIP_FILE not exist"
	exit 1
fi

if [ ! -e $VM_IMG ]; then
	usage "$VM_IMG not exist"
	exit 1
fi

echo "You are going to create image ($VM_IMG) for VM"
echo "You are going to format ($EXTRACT_DISK) as temporary extraction location"
echo "Please confirm that output image paths are correct !"
read -p "Continue ? [y/n]" yn
case $yn in
	[Yy]*) ;;
	[Nn]*) exit;;
esac

mkfs.ext4 $VM_IMG -F

if [ ! -e $EXTRACT_DISK ]; then
	usage "$EXTRACT_DISK not exist"
	exit 1
fi

mkfs.ext4 $EXTRACT_DISK -F

TEMP_DIR=/home/root/image

rm -rf $TEMP_DIR
mkdir -p $TEMP_DIR
mount $EXTRACT_DISK $TEMP_DIR

cd $TEMP_DIR
case $ZIP_FILE in
    *.zip) 7z x $ZIP_FILE;;
    *.tar.gz) tar -xvzf $ZIP_FILE;;
    *) echo "Please make sure the image suffix is ".gz" or "tar.gz"; exit"
            exit 0
    ;;
esac

simg2img super.img super.img.raw
mv super.img.raw super.img
simg2img config.img config.img.raw
mv config.img.raw config.img
cd -

SIZE_GB=$(fdisk -l $VM_IMG | grep Disk | awk '{print $3}')
SIZE_GB=$(awk "BEGIN {print int($SIZE_GB)}")
python3 ./create_gpt_image.py --create $VM_IMG --size=${SIZE_GB}G --flashfiles $TEMP_DIR
