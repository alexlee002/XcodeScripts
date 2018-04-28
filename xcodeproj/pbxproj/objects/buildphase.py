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
from xcodeproj.utils import func

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
            pbxhelper.pbxobj_set_pbxlist_attr(self, PBXBuildPhase, name, value, \
                self.is_valid_buildfile)
        else:
            super(PBXBuildPhase, self).__setattr__(name, value)        

    def comment(self):
        """ override """
        return self.displayname()

    def displayname(self):
        """ build phase's name, should be uniqued """
        self.pbx_name

    def _duplicate_attr(self, attr, val):
        if attr == u'pbx_files':
            for bf in val:
                obj.addfile(bf.duplicate())
        else:
            super(PBXBuildPhase, self)._duplicate_attr(attr, val)

    def allow_multi_owners(self):
        """ override """
        return True

    def _accepted_owner(self, obj):
        return isinstance(obj, PBXTarget) and obj.hasphase(self)

    def is_valid_buildfile(self, buildfile):
        """ build file validator """
        return isinstance(buildfile, baseobject.PBXBaseObject) and buildfile.isa == u'PBXBuildFile'

    def hasfile(self, buildfile):
        """
        return True if contains buildfile 
        :param  buildfile   guid or buildfile object
        """
        return pbxhelper.pbxobj_has_pbxlist_value(self, u'pbx_files', buildfile, \
            self.is_valid_buildfile)

    def add_file_reference(self, fileref, **kwargs): # kwargs=settings
        existsbf = None
        for bf in self.pbx_files:
            oldref = bf.pbx_fileRef
            if oldref is None:
                continue
            if oldref == fileref or \
                oldref.isa == fileref.isa and oldref.realpath() == fileref.realpath():
                existsbf = bf
                break
        if not existsbf is None:
            if u'settings' in kwargs:
                existsbf.pbx_settings = kwargs.get(u'settings')
            return existsbf

        from xcodeproj.pbxproj.objects import buildfile
        bf = buildfile.PBXBuildFile.new_buildfile(fileref)
        if u'settings' in kwargs:
            bf.pbx_settings = kwargs.get(u'settings')
        self.addfile(bf)
        return bf

    def addfile(self, buildfile, index=None):
        """ add buildfile to this phase """
        # if len(func.take(lambda o: o.realpath() == buildfile.realpath() and o.isa == buildfile.isa,\
        #     self.pbx_files)) == 0:
        pbxhelper.pbxobj_add_pbxlist_value(self, u'pbx_files', buildfile, \
            self.is_valid_buildfile, index=index)

    def removefile(self, buildfile):
        """ 
        remove buildfile 
        :param buildfile    buildfile object or guid to be removed
        """
        pbxhelper.pbxobj_remove_pbxlist_value(self, u'pbx_files', buildfile, self.is_valid_buildfile)

    def remove_all_files(self):
        """ remove all build files """
        self.pbx_files = []

    def _validate_files(self, resolved, issues):
        pbxhelper.pbxobj_validate_pbxlist_attr(\
            self, u'pbx_files', self.is_valid_buildfile, resolved=resolved, issues=issues)

        def __deduplicate_action(reserved, delitem):
            self.removefile(delitem)
            reserved.replace(delitem)

        pbxhelper.pbxobj_deduplicate_pbxlist_value(self, u'pbx_files', lambda f: f.realpath(), \
            __deduplicate_action, resolved, issues)

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

    def displayname(self):
        """ override """
        return self.pbx_name if not self.pbx_name is None else u'CopyFiles'

class PBXFrameworksBuildPhase(PBXBuildPhase):

    def displayname(self):
        """ override """
        return self.pbx_name if not self.pbx_name is None else u'Frameworks'


class PBXHeadersBuildPhase(PBXBuildPhase):

    def displayname(self):
        """ override """
        return self.pbx_name if not self.pbx_name is None else u'Headers'


class PBXResourcesBuildPhase(PBXBuildPhase):

    def displayname(self):
        """ override """
        return self.pbx_name if not self.pbx_name is None else u'Resources'


class PBXSourcesBuildPhase(PBXBuildPhase):
    
    def displayname(self):
        """ override """
        return self.pbx_name if not self.pbx_name is None else u'Sources'


class PBXShellScriptBuildPhase(PBXBuildPhase):
    def __init__(self, xcproj, guid):
        super(PBXShellScriptBuildPhase, self).__init__(xcproj, guid)
        self.pbx_inputPaths = [] # [str]
        self.pbx_outputPaths = [] # [str]
        self.pbx_shellPath = u'/bin/sh' # str
        self.pbx_shellScript = u'' # str

    def displayname(self):
        """ override """
        return self.pbx_name if not self.pbx_name is None else u'ShellScript'




