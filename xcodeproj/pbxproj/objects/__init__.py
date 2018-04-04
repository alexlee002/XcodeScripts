#!/usr/bin/python
# encoding:utf-8
# 
# copyright (c) Alex Lee, All rights reserved.

import os
import sys
ModuleRoot = os.path.abspath(os.path.join(__file__, '../../../..'))
if os.path.isdir(ModuleRoot) and not ModuleRoot in sys.path:
    sys.path.append(ModuleRoot)

from xcodeproj.pbxproj.objects.buildfile import *
from xcodeproj.pbxproj.objects.buildphase import *
from xcodeproj.pbxproj.objects.fileref import *
from xcodeproj.pbxproj.objects.group import *
from xcodeproj.pbxproj.objects.project import *
from xcodeproj.pbxproj.objects.target import *
from xcodeproj.pbxproj.objects.config import *
from xcodeproj.pbxproj.objects.dependency import *
from xcodeproj.pbxproj.objects.proxy import *