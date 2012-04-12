# -*- coding: utf-8 -*-
import os
from fabric.api import settings as fab_settings
from fabric.operations import local

try:
    from django.conf import settings
except ImportError:
    import settings
from wrapper import DVCSException

logging = settings.APP_LOGGER

def shell(cmd, capture=not settings.FABRIC_OUTPUT, ignore_return_code=False):
    logging.debug('Executing shell %s' % cmd)
    with fab_settings(warn_only=True):
        out = local(cmd, capture)
        if out.failed and not ignore_return_code:
            info = {'cmd': cmd, 'code': out.return_code, 'stderr': out.stderr.decode('utf8'),
                    'stdout': getattr(out, 'stdout', '').decode('utf8')}
            raise DVCSException('Executing %(cmd)s failed %(code)d stderr: %(stderr)s stdout:%(stdout)s' % info,
                **info)
        return out.decode('utf8', errors='ignore')


def touch(path):
    with file(path, 'a'):
        os.utime(path, None)
