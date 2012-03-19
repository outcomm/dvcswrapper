#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dvcs.settings.base import *
from dvcs.settings.prod import *

try:
    from dvcs.settings.local import *
except ImportError:
    pass


  