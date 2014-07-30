#!/usr/bin/env python
import sys
import json

# return a list of TARGET:$(TARGET) for each target found in .json
with open(sys.argv[1], 'r') as f:
    data = json.loads(f.read())

deps = []
for cmds in data['commands'].values():
    deps += [l['target'] for l in cmds if 'target' in l]

deps = [ d + ':$(' + d  + ')' for d in set(deps)]

print ' '.join(deps)
