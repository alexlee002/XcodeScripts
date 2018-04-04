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
from xcodeproj.pbxproj import baseobject
from xcodeproj.pbxproj import abstract
from xcodeproj.pbxproj import pbxhelper


def add_file(xcproj, path, targetobj, groupobj, copy=False):
    """
    add file/dir to project 'xcproj'. if the file with same realpath is exists, merge them
    """

    def __fileref_path_dict(xcproj):
        dic = dict()
        for file in xcproj.findobjects(\
            lambda o: o.pbx_isa in ['PBXFileReference', 'PBXVariantGroup']):
            key = '%s:%s' % (file.pbx_isa, file.realpath)
            dic[key] = file
        return dic
    #end __fileref_path_dict

    fileref_path_dict = __fileref_path_dict(xcproj)

    def __add_file(xcproj, path, targetobj, groupobj):
        parent_name, parent_ext = os.path.splitext(os.path.dirname(path))

        # create file reference
        fileref = func.dictval(fileref_path_dict, 'PBXFileReference:%s' % path)
        fileref_existed = True
        if fileref is None:
            fileref_existed = False
            fileref = file.PBXFileReference(xcproj.gen_uuid())
            fileref.realpath = path
            fileref.pbx_sourceTree = pbxconsts.SOURCE_TREE_ENMU.group
            fileref.pbx_lastKnownFileType = pbxhelper.get_filetype(path)
            assert not fileref.pbx_lastKnownFileType is None

        if parent_ext == '.lproj':
            if not fileref_existed:
                fileref.pbx_name = parent_name

            vgroup = func.dictval(fileref_path_dict, 'PBXVariantGroup:%s' % path)
            if vgroup is None:
                # create PBXVariantGroup
                vgroup = group.PBXVariantGroup(xcproj.gen_uuid())
                vgroup.addchild(fileref)
                vgroup.pbx_name = os.path.basename(path)
                vgroup.pbx_sourceTree = pbxconsts.SOURCE_TREE_ENMU.group
            # add to group
            groupobj.addchild(vgroup)
            fileref = vgroup
        else:
            # add to group
            groupobj.addchild(fileref)

        # create buildfile
        bf = file.PBXBuildFile(xcproj.gen_uuid())
        bf.setfileref(fileref)
        # add to buildphase
        bpisa = pbxhelper.buildphase_for_filetype(fileref.filetype())
        bps = targetobj.findbuildphase(lambda o: o.pbx_isa == bpisa)
        bp = bps[0] if len(bps) > 0 else None
        if bp is None:
            bp = buildphase.PBXResourcesBuildPhase(xcproj.gen_uuid())
            targetobj.addbuildphase(bp)
        bp.addfile(bf)
    #end of __add_file

    def __recursively_add(xcproj, path, targetobj, groupobj):
        if os.path.isdir(path):
            ext = os.path.splitext(path)[1]
            if ext in ['.bundle', '.xcassets', '.framework']:
                __add_file(xcproj, path, targetobj, groupobj)
            else:
                for fn in  os.listdir(path):
                    if func.hasprefix(fn, '.'):
                        continue

                    subpath = os.path.join(path, fn)
                    if not os.path.splitext(fn) == '.lproj':
                        # create child group
                        child = group.PBXGroup(xcproj.gen_uuid())
                        child.pbx_sourceTree = pbxconsts.SOURCE_TREE_ENMU.group
                        child.realpath = subpath
                        groupobj.addchild(child)

                    if not os.path.splitext(os.path.dirname(path))[1] == '.lproj':
                        __recursively_add(xcproj, subpath, targetobj, child)
        else:
            __add_file(xcproj, path, targetobj, groupobj)
    # end of __recursively_add


    path = os.path.abspath(path)

    if not func.issubpath(xcproj.project_dir(), path) and copy:
        dstpath = os.path.join(groupobj.realpath, os.path.basename(path))
        shutil.copytree(path, dstpath)
        path = dstpath

    __recursively_add(xcproj, path, targetobj, groupobj)