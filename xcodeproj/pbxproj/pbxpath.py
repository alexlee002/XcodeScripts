#!/usr/bin/python
# encoding:utf-8
# 
# copyright (c) Alex Lee, All rights reserved.

import os
import sys
ModuleRoot = os.path.abspath(os.path.join(__file__, '../../..'))
if os.path.isdir(ModuleRoot) and not ModuleRoot in sys.path:
    sys.path.append(ModuleRoot)

from xcodeproj.utils import func
from xcodeproj.utils import logger
from xcodeproj.pbxproj import pbxconsts


def normalize_abspath(path):
    """ normalize the path in xcodeproj """
    if path is None:
        return None

    import re
    match = re.search('(^(\s*)\$[\{\(]([\d\w_]+)[\}\)])', path)
    if match:
        repstr = match.group(1)
        envname = match.group(3)
        path = path.replace(repstr, (u'$({0})'.format(envname))) # trim left space
    else:
        path = os.path.join(u'$(SRCROOT)', os.path.normpath(path))
    return path

def abspath(obj):
    """ complete the path for obj: (PBXBuildFile, BPXFileReference, PBXGroup, ...)"""
    path = None
    source_tree = obj.pbx_sourceTree
    if source_tree == pbxconsts.SOURCE_TREE.group:
        owner = func.get_list_item(obj.owners(), 0)
        path = owner.abspath() if not owner is None else None
        if not path is None:
            objpath = os.path.normpath(obj.pbx_path if not obj.pbx_path is None else '')
            path = os.path.join(path, objpath)
    elif source_tree == pbxconsts.SOURCE_TREE.absolute:
        path = normalize_abspath(obj.path)
    else:
        path_mapper = {pbxconsts.SOURCE_TREE.SOURCE_ROOT: u'$(SOURCE_ROOT)',
                       pbxconsts.SOURCE_TREE.SDKROOT: u'$(SDKROOT)',
                       pbxconsts.SOURCE_TREE.DEVELOPER_DIR: u'$(DEVELOPER_DIR)',
                       pbxconsts.SOURCE_TREE.BUILT_PRODUCTS_DIR: u'$(BUILT_PRODUCTS_DIR)'}

        if source_tree in path_mapper:
            objpath = os.path.normpath(obj.pbx_path if not obj.pbx_path is None else '')
            path = os.path.join(path_mapper[source_tree], objpath)
        else:
            raise ValueError('{0} Unknown sourceTree: {1}'.format(obj, source_tree))
    return path

def realpath(xcproj, objpath):
    """ parse the object's abspath('objpath') to the real path on disk by replacing the env-vars """
    if objpath is None or xcproj is None:
        return None

    import re
    match = re.search('(^(\s*)\$[\{\(]([\d\w_]+)[\}\)])', objpath)
    if match:
        repstr = match.group(1)
        envname = match.group(3)
        envval = xcproj.buildsettings(envname)
        if not envval is None:
            objpath = os.path.normpath(objpath.replace(repstr, envval))
        else:
            objpath = objpath.replace(repstr, (u'$({env})'.format(env=envname))) # trim left space
    else:
        projdir = xcproj.buildsettings(u'SRCROOT')
        if projdir is None:
            projdir = xcproj.buildsettings(u'PROJECT_DIR')
        if projdir is None:
            objpath = os.path.join(u'$(SRCROOT)', os.path.normpath(objpath))
        else:
            objpath = os.path.normpath(os.path.join(projdir, objpath))

    return objpath





# from xcodeproj.pbxproj import baseobject
# from xcodeproj.pbxproj.objects import *