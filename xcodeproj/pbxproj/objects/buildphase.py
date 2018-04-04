#!/usr/bin/python
# encoding:utf-8
# 
# copyright (c) Alex Lee, All rights reserved.

import os
import sys
ModuleRoot = os.path.abspath(os.path.join(__file__, '../../../..'))
if os.path.isdir(ModuleRoot) and not ModuleRoot in sys.path:
    sys.path.append(ModuleRoot)


from xcodeproj.pbxproj import baseobject
from xcodeproj.pbxproj import pbxhelper
from xcodeproj.utils import logger

class PBXBuildPhase(baseobject.PBXBaseObject):
    """ 
    this is a virtual parent node 

    owner:    PBXNativeTarget
    relative:    many to many    

    pbx-attr:
        files               [PBXBuildFile], notnull, default []
        buildActionMask     int, nonnull, default 2147483647 (?)
        runOnlyForDeploymentPostprocessing  int, nonnull, default 0
        name                str, nullable,
    """

    def __init__(self, xcproj, guid):
        super(PBXBuildPhase, self).__init__(xcproj, guid)
        self.pbx_files = []
        self.pbx_buildActionMask = 2147483647 # int
        self.pbx_runOnlyForDeploymentPostprocessing = 0 # int

    def __setattr__(self, name, value):
        if name == u'pbx_files':
            pbxhelper.set_pbxobj_list_value(self, PBXBuildPhase, name, value, self.is_valid_buildfile)
        else:
            super(PBXBuildPhase, self).__setattr__(name, value)

    def comment(self):
        """ override """
        return self.pbx_name

    def duplicate(self):
        """ override """
        obj = super(PBXBuildPhase, self).duplicate()
        for attr, val in self.__dict__.items():
            if attr == u'pbx_files':
                for bf in val:
                    obj.addfile(bf.duplicate())
            elif func.hasprefix(attr, pbxconsts.PBX_ATTR_PREFIX):
                setattr(obj, attr, val)
        return obj

    def allow_multi_owners(self):
        """ override """
        return True

    def _accepted_owner(self, obj):
        return isinstance(obj, PBXTarget) and obj.hasphase(self)

    def is_valid_buildfile(self, buildfile):
        return isinstance(buildfile, baseobject.PBXBaseObject) and buildfile.isa == u'PBXBuildFile'

    def hasfile(self, buildfile):
        """
        return True if contains buildfile 
        :param  buildfile   guid or buildfile object
        """
        return pbxhelper.pbxobj_has_list_value(self, u'pbx_files', buildfile, \
            self.is_valid_buildfile)

    def addfile(self, buildfile, index=None):
        """ add buildfile to this phase """
        pbxhelper.pbxobj_add_list_value(self, u'pbx_files', buildfile, self.is_valid_buildfile, \
            index=index)

    def removefile(self, buildfile):
        """ 
        remove buildfile 
        :param buildfile    buildfile object or guid to be removed
        """
        pbxhelper.pbxobj_remove_list_value(self, u'pbx_files', buildfile, self.is_valid_buildfile)

    def _validate_files(self, resolved, issues):
        path_dict = dict() # {realpath: obj}
        for obj in list(self.pbx_files):
            try:
                obj.validate()
            except Exception as e:
                if obj is None or isinstance(e, baseobject.PBXValidationError):
                    self.removefile(obj)
                    resolved.append(u'remove invalid buildfile {0}: {1}'.format(obj, e))
                    continue
                else:
                    raise

            realpath = obj.realpath()
            if not realpath in path_dict:
                path_dict[realpath] = [obj]
            else:
                path_dict[realpath].append(obj)

        for path, objs in path_dict.items():
            if len(objs) > 1:
                removingobjs = objs if path is None else objs[1:]
                for obj in removingobjs:
                    self.removefile(obj)
                resolved.append(\
                    u'remove duplicate buildfile of path "{path}"\n\t{objs}'\
                    .format(path=path, objs=u'\n\t'.join([str(o) for o in removingobjs])))

    def _validate(self):
        """ override """
        resolved, issues = super(PBXBuildPhase, self)._validate()
        self._validate_files(resolved, issues)
        return resolved, issues


class PBXCopyFilesBuildPhase(PBXBuildPhase):
    def __init__(self, xcproj, guid):
        super(PBXCopyFilesBuildPhase, self).__init__(xcproj, guid)
        self.pbx_dstPath = u'' # str
        self.pbx_dstSubfolderSpec = 0 # int

    def comment(self):
        """ override """
        return self.pbx_name if not self.pbx_name is None else u'CopyFiles'

class PBXFrameworksBuildPhase(PBXBuildPhase):

    def comment(self):
        """ override """
        return self.pbx_name if not self.pbx_name is None else u'Frameworks'


class PBXHeadersBuildPhase(PBXBuildPhase):

    def comment(self):
        """ override """
        return self.pbx_name if not self.pbx_name is None else u'Headers'


class PBXResourcesBuildPhase(PBXBuildPhase):

    def comment(self):
        """ override """
        return self.pbx_name if not self.pbx_name is None else u'Resources'


class PBXSourcesBuildPhase(PBXBuildPhase):
    
    def comment(self):
        """ override """
        return self.pbx_name if not self.pbx_name is None else u'Sources'


class PBXShellScriptBuildPhase(PBXBuildPhase):
    def __init__(self, xcproj, guid):
        super(PBXShellScriptBuildPhase, self).__init__(xcproj, guid)
        self.pbx_inputPaths = [] # [str]
        self.pbx_outputPaths = [] # [str]
        self.pbx_shellPath = u'/bin/sh' # str
        self.pbx_shellScript = u'' # str

    def comment(self):
        """ override """
        return self.pbx_name if not self.pbx_name is None else u'ShellScript'




