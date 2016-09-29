#!/bin/sh

if [ "x$SIMICS_BASE_PACKAGE" != "x" ]; then
    DIR="$SIMICS_BASE_PACKAGE/bin/`basename "$0"`"
else
    DIR="$0"
fi

case `uname` in
    CYGWIN*)
	DIR="`cygpath "$0"`"
	;;
esac

SCRIPTSDIR="`dirname "$DIR"`"
SCRIPTSDIR="`cd "$SCRIPTSDIR"; pwd`" # allow convoluted start paths
if [ "$SCRIPTSDIR" = "." ] ; then
    HOSTSDIR="`cd .. ; pwd`"
else
    # find HOSTSDIR in a way that works when running from a user-install
    HOSTSDIR="$(dirname "$SCRIPTSDIR")"
    HOSTSDIR="$(cd "$HOSTSDIR" ; pwd)"
fi

USER_SET_HOST=$SIMICS_HOST
SIMICS_HOST="$(sh "$HOSTSDIR"/scripts/host-type.sh 2> /dev/null)"

if [ -z "$SIMICS_HOST" ] ; then
    SIMICS_HOST=$USER_SET_HOST
    echo "The Simics start-script failed to find a matching host for Simics."
    if [ -z "$USER_SET_HOST" ] ; then
	echo "Set the SIMICS_HOST environment variable to set the host" \
	    "manually."
    fi
    echo "Error message:" `sh $HOSTSDIR/scripts/host-type.sh 2>&1`
    echo ""
    exit 1
fi

BINDIR="$HOSTSDIR/$SIMICS_HOST/bin"
