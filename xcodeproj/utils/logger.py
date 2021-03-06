#!/usr/bin/python
# encoding:utf-8
# 
# copyright (c) Alex Lee, All rights reserved.

import os
import sys
ModuleRoot = os.path.abspath(os.path.join(__file__, '../../..'))
if os.path.isdir(ModuleRoot) and not ModuleRoot in sys.path:
    sys.path.append(ModuleRoot)

from xcodeproj.utils import template
from xcodeproj.utils import func

adaptor = template.enum(SHELL=0, XCODE=1)
level = template.enum(VERBOSE=0, INFO=1, WARN=2, ERROR=3)

ENABLE_DEBUG = False
LOG_LEVEL = level.VERBOSE
ADAPTOR = adaptor.SHELL if os.getenv(u'PROJECT_DIR') is None else adaptor.XCODE

def __logmsg(lvl, msg, detail=False):
    if lvl < LOG_LEVEL:
        return

    if detail:
        func, file, line = func.callerinfo(2)
        msg = '{func}({file}:{line}) {msg}'.format(func=func, file=file, line=line, msg=msg)

    if ADAPTOR == adaptor.SHELL:
        if lvl == level.VERBOSE:
            msg = '\033[2m-[V] {0}\033[0m'.format(msg)
        elif lvl == level.INFO:
            msg = '\033[32m-[I] {0}\033[0m'.format(msg)
        elif lvl == level.WARN:
            msg = '\033[33m-[W] {0}\033[0m'.format(msg)
        elif lvl == level.ERROR:
            msg = '\033[1;31m-[E] {0}\033[0m'.format(msg)
    else:
        if lvl == level.WARN:
            msg = 'warning: {0}'.format(msg)
        elif lvl == level.ERROR:
            msg = 'error: {0}'.format(msg)

    return msg


def verbose(msg):
    sys.stdout.writelines([__logmsg(level.VERBOSE, msg, detail=ENABLE_DEBUG), os.linesep])

def info(msg):
    sys.stdout.writelines([__logmsg(level.INFO, msg, detail=ENABLE_DEBUG), os.linesep])

def warn(msg):
    sys.stdout.writelines([__logmsg(level.WARN, msg, detail=ENABLE_DEBUG), os.linesep])

def error(msg):
    sys.stderr.writelines([__logmsg(level.ERROR, msg, detail=ENABLE_DEBUG), os.linesep])



