#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    "--config merge-tools.e.args='$base $local $other $output'",
    "--config merge-tools.e.priority=1000",
    "--config merge-tools.e.executable=%s" % os.path.join(SCRIPT_DIR, 'mergetool.py'),
    "--config merge-tools.e.premerge=True",
"""

import sys

try:
    import simplejson as json
except ImportError:
    import json

base = sys.argv[1]
local = sys.argv[2]
other = sys.argv[3]
tar = sys.argv[4]

out = {'base': base, 'local': local, 'other': other, 'tar': tar}

out = json.dumps(out)
print out




