#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Because hg doesn't support outputting currently diffed files content to stdout
we need to exploit extdiff extension (bundled w/ hg) which pipes file names to
external program like this:
    hg extdiff -p echo bitchesbrew/core/bb.py -r50:45
"""

import sys, difflib
from utils import read_file

first = read_file(sys.argv[1])
second = read_file(sys.argv[2])

print difflib.HtmlDiff().make_table(first.splitlines(),second.splitlines())

