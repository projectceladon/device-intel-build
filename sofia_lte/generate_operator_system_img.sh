#
# OPERATOR CUSTOMIZATION SCRIPT
#
echo "---------------------------start gen_operator_system_img.sh-----------------------"
echo $PWD
OUT_PROCUCT_DIR=$PWD/out/target/product/$TARGET_PRODUCT
SEARCH_DIR=$PWD/device/intel-imc/sofia_lte/SwSc/OperatorConfigs
##############save default file###########
DEFAULT_BOOTANIM_ZIP=$OUT_PROCUCT_DIR/system/media/bootanimation.zip
DEFAULT_BOOTANIM_BACKUP_ZIP=$OUT_PROCUCT_DIR/bootanimation_bakcup.zip
if [ -f $DEFAULT_BOOTANIM_ZIP ] ;then
    cp -fv $DEFAULT_BOOTANIM_ZIP $DEFAULT_BOOTANIM_BACKUP_ZIP
fi

DEFAULT_SHUTANIM_ZIP=$OUT_PROCUCT_DIR/system/media/shutdownanimation.zip
DEFAULT_SHUTANIM_BACKUP_ZIP=$OUT_PROCUCT_DIR/shutdownanimation_bakcup.zip
if [ -f $DEFAULT_SHUTANIM_ZIP ] ;then
    cp -fv $DEFAULT_SHUTANIM_ZIP $DEFAULT_SHUTANIM_BACKUP_ZIP
fi
mv $OUT_PROCUCT_DIR/system.img $OUT_PROCUCT_DIR/system_backup.img
##########################################
for OUT_FILE in `ls -p $SEARCH_DIR`
do
    echo "\n"---------------------------------------------------
    echo "\n" GEN system.fls for -- $OUT_FILE
    echo "\n"---------------------------------------------------

    mkdir -p $OUT_PROCUCT_DIR/fls/fls/$OUT_FILE
    chmod 777 $OUT_PROCUCT_DIR/fls/fls/$OUT_FILE

    #make sure to use lower case operator name
    operator=$(echo $OUT_FILE | tr '[A-Z]' '[a-z]' )
    OPERATOR_BOOTANIM_FILE=${3}/bootanimation_operators/bootanimation_${operator}.zip
    OPERATOR_SHUTANIM_FILE=${3}/shutanimation_operators/shutdownanimation_${operator}.zip
    if [ -f $OPERATOR_BOOTANIM_FILE ] ;then
        echo "[making operator system.fls ] Found " $OPERATOR_BOOTANIM_FILE "generating operator system.fls for " $OUT_FILE
        cp  -fv $OPERATOR_BOOTANIM_FILE $DEFAULT_BOOTANIM_ZIP
    fi
    if [ -f $OPERATOR_SHUTANIM_FILE ] ;then
        echo "[making operator system.fls ] Found " $OPERATOR_SHUTANIM_FILE "generating operator system.fls for " $OUT_FILE
        cp  -fv $OPERATOR_SHUTANIM_FILE $DEFAULT_SHUTANIM_ZIP
    fi
    if [ -f $OPERATOR_BOOTANIM_FILE -o -f $OPERATOR_SHUTANIM_FILE ] ;then
       make snod
       rm  -rfv $OUT_PROCUCT_DIR/fls/fls/$OUT_FILE/system.fls
       $PWD/device/intel-imc/common/tools/FlsTool --prg $1 --output $OUT_PROCUCT_DIR/fls/fls/$OUT_FILE/system.fls --tag SYSTEM $2 $OUT_PROCUCT_DIR/system.img --replace --to-fls2
    fi
done
##############restore default file###########

if [ -f $DEFAULT_BOOTANIM_BACKUP_ZIP ] ;then
    cp -fv $DEFAULT_BOOTANIM_BACKUP_ZIP $DEFAULT_BOOTANIM_ZIP
    rm -fv $DEFAULT_BOOTANIM_BACKUP_ZIP
else
    rm $DEFAULT_BOOTANIM_ZIP
fi

if [ -f $DEFAULT_SHUTANIM_BACKUP_ZIP ] ;then
    cp -fv $DEFAULT_SHUTANIM_BACKUP_ZIP $DEFAULT_SHUTANIM_ZIP
    rm -fv $DEFAULT_SHUTANIM_BACKUP_ZIP
else
    rm $DEFAULT_SHUTANIM_ZIP
fi
rm  -fv $OUT_PROCUCT_DIR/system.img
mv $OUT_PROCUCT_DIR/system_backup.img $OUT_PROCUCT_DIR/system.img
############################################

echo "-------------------------end gen_operator_system_img.sh----------------------------"
