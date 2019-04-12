FROM ubuntu:14.04
ARG userid
ARG groupid
ARG username
ARG http_proxy
ARG https_proxy

ENV http_proxy  $http_proxy
ENV https_proxy $https_proxy

RUN echo "Acquire::http::proxy \"$http_proxy\";" > /etc/apt/apt.conf
RUN echo "Acquire::https::proxy \"$https_proxy\";" >> /etc/apt/apt.conf

RUN apt-get update && apt-get install -y git-core gnupg flex bison gperf build-essential zip curl zlib1g-dev gcc-multilib g++-multilib libc6-dev-i386 lib32ncurses5-dev x11proto-core-dev libx11-dev lib32z-dev ccache libgl1-mesa-dev libxml2-utils xsltproc unzip python openjdk-7-jdk

# Intel BSP specific packages for gordon_peak target
RUN apt-get install -y bc python-mako gettext python-pip libssl-dev libelf-dev liblz4-tool dos2unix
RUN pip install --upgrade pip --proxy $http_proxy
RUN pip install --upgrade cryptography -t /usr/lib/python2.7/dist-packages --proxy $http_proxy

# Intel BSP specific packages for UEFI targets
RUN apt-get install -y sbsigntool dosfstools mtools

#RUN curl -o jdk8.tgz https://android.googlesource.com/platform/prebuilts/jdk/jdk8/+archive/master.tar.gz \
# && tar -zxf jdk8.tgz linux-x86 \
# && mv linux-x86 /usr/lib/jvm/java-8-openjdk-amd64 \
# && rm -rf jdk8.tgz

#RUN curl -o /usr/local/bin/repo https://storage.googleapis.com/git-repo-downloads/repo \
# && echo "e147f0392686c40cfd7d5e6f332c6ee74c4eab4d24e2694b3b0a0c037bf51dc5  /usr/local/bin/repo" | sha256sum --strict -c - \
# && chmod a+x /usr/local/bin/repo

RUN curl -o /usr/local/bin/repo https://android.intel.com/static/repo \
 && chmod a+x /usr/local/bin/repo

RUN groupadd -g $groupid $username \
 && useradd -m -u $userid -g $groupid $username \
 && echo "$username:123456" | chpasswd \
 && echo $username >/root/username \
 && echo "$username ALL=NOPASSWD:ALL" >> /etc/sudoers
COPY gitconfig /home/$username/.gitconfig
RUN chown $userid:$groupid /home/$username/.gitconfig
COPY ssh /home/$username/.ssh
RUN chown -R $userid:$groupid /home/$username/.ssh
ENV HOME=/home/$username
ENV USER=$username

ENTRYPOINT chroot --userspec=$(cat /root/username):$(cat /root/username) / /bin/bash -i
