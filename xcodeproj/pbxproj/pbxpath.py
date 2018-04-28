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

PATH_ENV_REG = u'(^(\s*)\$[\{\(]?([\d\w_]+)[\}\)]?)'

def is_variant_path(path):
    import re
    return re.search(PATH_ENV_REG, path)

def normalize_path(path, autocomplete=True):
    """ normalize the path in xcodeproj """
    if path is None:
        return None

    import re
    match = re.search(PATH_ENV_REG, path)
    if match:
        repstr = match.group(1)
        envname = match.group(3)
        subpath = os.path.relpath(path, repstr)
        subpath_comps = filter(lambda o:len(o) > 0, subpath.split(os.sep))
        if len(subpath_comps) == 0 or (len(subpath_comps) == 1 and subpath_comps[0] == u'.'):
            path = u'$({0})'.format(envname)
        else:
            subpath = os.sep.join(subpath_comps)
            path = os.path.join(u'$({0})'.format(envname), subpath) # trim left space

    else:
        path = os.path.normpath(path)
        if autocomplete:
            path = os.path.join(u'$(SRCROOT)', path)
    return path

def abspath(obj):
    """ complete the path for obj: (PBXBuildFile, BPXFileReference, PBXGroup, ...)"""
    path = None
    source_tree = obj.pbx_sourceTree
    if source_tree == pbxconsts.SOURCE_TREE.group:
        owner = func.get_list_item(obj.owners().values(), 0)
        path = owner.abspath() if not owner is None else None
        if not path is None and not obj.pbx_path is None:
            objpath = os.path.normpath(obj.pbx_path)
            path = os.path.join(path, objpath)
    elif source_tree == pbxconsts.SOURCE_TREE.absolute:
        path = normalize_path(obj.path)
    else:
        path_mapper = {pbxconsts.SOURCE_TREE.source_root: u'$(SOURCE_ROOT)',
                       pbxconsts.SOURCE_TREE.sdkroot: u'$(SDKROOT)',
                       pbxconsts.SOURCE_TREE.developer_dir: u'$(DEVELOPER_DIR)',
                       pbxconsts.SOURCE_TREE.built_products_dir: u'$(BUILT_PRODUCTS_DIR)'}

        if source_tree in path_mapper:
            objpath = os.path.normpath(obj.pbx_path if not obj.pbx_path is None else '')
            path = os.path.join(path_mapper[source_tree], objpath)
        else:
            raise ValueError('{0} Unknown sourceTree: {1}'.format(obj, source_tree))
    return path

def realpath(xcproj, objpath):
    """ 
    parse the object's abspath('objpath') to the abspath on disk by replacing the env-vars 
    """
    if objpath is None or xcproj is None:
        return None

    import re
    match = re.search(PATH_ENV_REG, objpath)
    if match:
        repstr = match.group(1)
        envname = match.group(3)
        envval = xcproj.buildsettings(envname)
        if not envval is None:
            objpath = os.path.normpath(objpath.replace(repstr, envval))
        else:
            subpath = os.path.relpath(objpath, repstr)
            objpath = os.path.join(u'$({0})'.format(envname), subpath)
    else:
        projdir = xcproj.buildsettings(u'SRCROOT')
        if projdir is None:
            projdir = xcproj.buildsettings(u'PROJECT_DIR')
        if projdir is None:
            objpath = os.path.join(u'$(SRCROOT)', os.path.normpath(objpath))
        else:
            objpath = os.path.normpath(os.path.join(projdir, objpath))

    return objpath


def issubpath(subpath, parent):
    """ return True if 'subpath' is subpath of 'parent' """
    import os
    
    parent = normalize_path(parent, autocomplete=False)
    subpath = normalize_path(subpath, autocomplete=False)
    return func.hasprefix(subpath, parent + os.sep)


def set_path_with_source_tree(obj, path, source_tree=pbxconsts.SOURCE_TREE.group, \
    parent_group=None):
    path = normalize_path(path)
    if source_tree == pbxconsts.SOURCE_TREE.group:
        from xcodeproj.pbxproj.objects import group
        assert isinstance(parent_group, group.PBXGroup)
        obj.pbx_path = os.path.relpath(path, parent_group.realpath())
    elif source_tree == pbxconsts.SOURCE_TREE.source_root:
        obj.pbx_path = os.path.relpath(path, obj.project().project_dir())
    else:
        obj.pbx_path = path
    obj.pbx_sourceTree = source_tree


def set_group_file_path(obj, objtype, path):
    path = normalize_path(path, autocomplete=False)
    if not path == u'.':
        super(objtype, obj).__setattr__(u'pbx_path', path)
    if obj.pbx_name is None and os.sep in path:
        dirname, dirext = os.path.splitext(os.path.dirname(path))
        if dirext == u'.lproj':
            obj.pbx_name = dirname
        else:
            obj.pbx_name = os.path.basename(path)



# from xcodeproj.pbxproj import baseobject
# from xcodeproj.pbxproj.objects import *