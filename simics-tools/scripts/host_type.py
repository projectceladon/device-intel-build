#!/usr/bin/python

# This Software is part of Wind River Simics. The rights to copy, distribute,
# modify, or otherwise make use of this Software may be licensed only
# pursuant to the terms of an applicable Wind River license agreement.
# 
# Copyright 2010-2016 Intel Corporation

# Platform-independent and import-able Python interface to host-type.sh.

from subprocess import Popen, PIPE
import os, sys
import simicsutils.host

class HostTypeError(Exception): pass

def host_type(simics_root):
    if simicsutils.host.is_windows():
        # sh is not available, so instead emulate the behavior of host-type.sh
        return os.environ.get('SIMICS_HOST', simicsutils.host.host_type())
    host_type_sh = os.path.join(simics_root, "scripts", "host-type.sh")
    if not os.path.isfile(host_type_sh):
        raise HostTypeError("Invalid simics_root: Script '%s' not found"
                            % host_type_sh)

    proc = Popen([host_type_sh], stdout = PIPE, stderr = PIPE)
    (stdout, stderr) = proc.communicate()
    if proc.returncode == 0:
        return stdout.rstrip()
    else:
        raise HostTypeError("%s failed: " % host_type_sh + stderr)

if __name__ == "__main__":
    simics_root = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
    try:
        result = host_type(simics_root)
    except HostTypeError, e:
        sys.stderr.write(e.message)
        exit(1)
    sys.stdout.write(result + "\n")
