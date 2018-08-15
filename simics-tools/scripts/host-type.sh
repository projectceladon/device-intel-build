#!/bin/sh

OS=`uname -s`
HOST_ARCH=`uname -m`

SCRIPTSDIR="`dirname "$0"`"
SIMICS_ROOT="`cd "$SCRIPTSDIR"/.. ; pwd`"

case $HOST_ARCH in
    i*86)
        BITS="32"
	;;
    x86_64|amd64)
        BITS="64 32"
	;;
    *)
        echo "Unsupported architecture: $HOST_ARCH" >&2
	exit 1
	;;
esac

case $OS in
    Linux)
        OS_PART=linux
	;;
    CYGWIN_NT*WOW64)
        OS_PART=win
        # Cygwin is only a 32 bit application, which causes the host arch
        # detection to go wrong, so override it here
        BITS="64 32"
	;;
    CYGWIN_NT*)
        OS_PART=win
	;;
    *)
        echo "Unsupported OS: $OS" >&2
	exit 1
	;;
esac


# should be renamed to SIMICS_HOST_DIR (bug 10827)
# <add id="environment variable">
# <dt><tt>SIMICS_HOST</tt></dt>
# <dd>
# Overrides the host type detected by Simics. The value must be the
# name of the directory containing the host-specific files of a Simics
# installation. Typically a string on the form arch-os, e.g.,
# linux32.
# </dd></add>
if [ -n "$SIMICS_HOST" ]; then
    if [ -d "$SIMICS_ROOT/$SIMICS_HOST/bin"  ]; then
	echo $SIMICS_HOST
	exit 0
    else
	echo "Non-existing host $SIMICS_HOST." >&2
	exit 1
    fi
else
    for bits in $BITS; do
	host=$OS_PART$bits
	if [ -d "$SIMICS_ROOT/$host/bin" ]; then
	    echo $host
	    exit 0
	fi
    done
    echo "No matching host found." >&2
    exit 1
fi
