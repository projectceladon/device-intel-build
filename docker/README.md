The Dockerfile in this directory sets up an Ubuntu Trusty image ready to build
a variety of Android branches (>= Lollipop). It's particulary useful to build
older branches that required 14.04 if you've upgraded to something newer.

First, build the image:
```
# Copy your host gitconfig, or create a stripped down version
$ cp ~/.gitconfig gitconfig
$ cp -r ~/.ssh ssh
$ docker build --network host --build-arg userid=$(id -u) --build-arg groupid=$(id -g) --build-arg username=$(id -un) --build-arg http_proxy=$http_proxy --build-arg https_proxy=$https_proxy -t android-build-trusty .
```

Then you can start up new instances with:
```
$ export ANDROID_BUILD_TOP=xxx # set your source code path
$ docker run -it --network host --rm -v $ANDROID_BUILD_TOP:/src android-build-trusty
> cd /src; source build/envsetup.sh
> lunch   # choose your lunch target
> make -j droid dist
```
