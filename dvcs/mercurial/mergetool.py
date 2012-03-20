#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    "--config merge-tools.e.args='$base $local $other $output'",
    "--config merge-tools.e.priority=1000",
    "--config merge-tools.e.executable=%s" % os.path.join(SCRIPT_DIR, 'mergetool.py'),
    "--config merge-tools.e.premerge=True",
"""

from tempfile import mkstemp
import sys
from utils import read_file


try:
    import simplejson as json
except ImportError:
    import json

base = sys.argv[1]
local = sys.argv[2]
other = sys.argv[3]
tar = sys.argv[4]

def copy_to_my_tmp(file_name):
    f, name = mkstemp()
    with open(name,'w') as tmp:
        tmp.write(read_file(file_name))
    return name

out = {'base': copy_to_my_tmp(base),
       'local': copy_to_my_tmp(local),
       'other': copy_to_my_tmp(other),
       'tar': tar}

out = json.dumps(out)
print out




