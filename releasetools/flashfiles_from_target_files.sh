#!/bin/bash

echo "========================"
echo "Preparing flashfiles - New Method"
echo "No more Zip. We use tar + pigz"
echo "========================"

## PRE-REQUISITE
flashfile=`basename $1`
flashfile_dir=`echo $flashfile | sed 's/\.tar\.gz//g'`
PRODUCT_OUT=`dirname $1`
VARIANT=`grep -i "ro.system.build.type=" $PRODUCT_OUT/system/build.prop | cut -d '=' -f2`
TARGET=`grep -i "ro.build.product=" $PRODUCT_OUT/system/build.prop | cut -d '=' -f2`
ANDROID_ROOT=${PWD}

for arg in "$@"
do
    case $arg in
        RELEASE_BUILD=*)
        RELEASE_BUILD="${arg#*=}"
        shift
        ;;
    esac
done

echo "========================"
echo "Images / Files to be packed"
echo "========================"
IMAGES_TUPLE=`./device/intel/build/releasetools/flash_cmd_generator.py device/intel/project-celadon/$TARGET/flashfiles.ini $TARGET $VARIANT | tail -1`
c=0
for i in $IMAGES_TUPLE
do
  if [[ $c -gt 0 && `expr $c % 2` == 1 ]]; then
    i=`echo ${i::-3} | sed "s/'//g"`
    echo $i
    j="$j $i"
  fi
  c=$((c+1))
done

IMAGES=`echo $j | xargs -n1 | sort -u`
echo "========================"
echo "Generating Tar ..."
echo "========================"
cd $PRODUCT_OUT
rm -rf $flashfile_dir
mkdir $flashfile_dir

for i in $IMAGES
do
	echo "Adding $i"
	if [[ $i == "super.img" ]]; then
		SUPER_IMG=true
		if [[ "$RELEASE_BUILD" == "true" ]]; then
			cp  release_sign/super.img $flashfile_dir/.
		else
			cp ./obj/PACKAGING/super.img_intermediates/super.img $flashfile_dir/.
		fi
	else
		if [[ $i == "installer.efi" ]]; then
			cp efi/installer.efi $flashfile_dir/.
		else
			if [[ $i == "startup.nsh" ]]; then
				cp efi/startup.nsh $flashfile_dir/.
			elif [[ $i == "gpt.ini"  || $i == "gpt_ro.bin" || $i == "gpt_rw.bin" || $i == "gpt_rw_nolic.bin" ]]; then
				cp obj/PACKAGING/flashfiles_intermediates/root/$i $flashfile_dir/.
			else
				if [[ $i == "boot.img" || $i == "odm.img" || $i == "vbmeta.img" || $i == "vendor_boot.img" ]]; then
					if [[ "$RELEASE_BUILD" == "true" ]]; then
						cp ff_temp/IMAGES/$i $flashfile_dir/.
					else
						cp obj/PACKAGING/target_files_intermediates/$TARGET-target_files-*/IMAGES/$i $flashfile_dir/.
					fi
				else
					cp $i $flashfile_dir/.
				fi
			fi
		fi
	fi
done

cd $ANDROID_ROOT
echo "========================"
echo "Generate installer.cmd"
echo "========================"
device/intel/build/releasetools/flash_cmd_generator.py device/intel/project-celadon/$TARGET/flashfiles.ini $TARGET $VARIANT | sed '$d' | sed '$d' | sed -n '/installer.cmd/,$p' | sed '1d' > $PRODUCT_OUT/$flashfile_dir/installer.cmd

echo "========================"
echo "Generate flash.json"
echo "========================"
device/intel/build/releasetools/flash_cmd_generator.py device/intel/project-celadon/$TARGET/flashfiles.ini $TARGET $VARIANT | sed -n '/installer.cmd/q;p' | sed '1d' > $PRODUCT_OUT/$flashfile_dir/flash.json

if [[ $SUPER_IMG == "true" ]]; then
  cd $PRODUCT_OUT
  rm -f $flashfile_dir/system.img $flashfile_dir/vendor.img $flashfile_dir/product.img
fi

tar -cvf - -C $flashfile_dir/ . | /usr/bin/pigz > $flashfile

echo "========================"
echo "Flashfiles Tar $PRODUCT_OUT/$flashfile created"
echo "========================"
