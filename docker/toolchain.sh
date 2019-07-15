# Google specific packages for Android Build Environment
sudo apt-get update
sudo apt-get install -y git-core gnupg flex bison gperf build-essential zip curl zlib1g-dev gcc-multilib g++-multilib libc6-dev-i386 lib32ncurses5-dev x11proto-core-dev libx11-dev lib32z-dev libgl1-mesa-dev libxml2-utils xsltproc unzip python-networkx 

# Intel BSP specific packages for Android Build Environment
sudo apt-get install -y bc python-mako gettext python-pip libssl-dev libelf-dev liblz4-tool dos2unix ccache python openjdk-7-jdk

sudo pip install --upgrade pip --proxy $http_proxy
sudo pip install --upgrade cryptography -t /usr/lib/python2.7/dist-packages --proxy $http_proxy
sudo pip install mako

