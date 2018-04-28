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
from xcodeproj.pbxproj import pbxpath
from xcodeproj.pbxproj import pbxconsts
from xcodeproj.pbxproj import pbxhelper
from xcodeproj.utils import func

class PBXFileReference(baseobject.PBXBaseObject):
    """
    Project files

    owner:    PBXGroup
    relative:    one[group] to many[fileref]

    referrer:    PBXBuildFile
    relative:    many[buildFile] to one[fileRef]

    pbx-attr:
        fileEncoding        int, nullable
        lastKnownFileType   str, nullable
        name                str, nullable
        path                str, nullable
        sourceTree          str, nonnull, default '<group>'
        explicitFileType    str, nullable
        includeInIndex      int, nullable
        xcLanguageSpecificationIdentifier   str, nullable
        lineEnding          int, nullable
        wrapsLines          int, nullable

    """
    def __init__(self, xcproj, guid):
        super(PBXFileReference, self).__init__(xcproj, guid)
        self.pbx_sourceTree = pbxconsts.SOURCE_TREE.group # str; 
        # self.__realpath = None # str, real path on disk
        self.__abspath = None # str, project relative path

    def __setattr__(self, name, value):
        if name == u'pbx_path':
            pbxpath.set_group_file_path(self, PBXFileReference, value)
        else:
            super(PBXFileReference, self).__setattr__(name, value)

    def _accepted_owner(self, obj):
        """ override """
        from xcodeproj.pbxproj.objects import group
        return isinstance(obj, group.PBXGroup) and obj.haschild(self)

    def _print_in_one_line(self):
        return True

    def filetype(self):
        """ return file type or None """
        if not self.pbx_explicitFileType is None:
            return self.pbx_explicitFileType
        elif self.pbx_lastKnownFileType is None:
            self.pbx_lastKnownFileType = pbxhelper.get_filetype(self.realpath())
        return self.pbx_lastKnownFileType

    def abspath(self):
        """ return path in project """
        if self.__abspath is None:
            self.__abspath = pbxpath.abspath(self)
        return self.__abspath

    def realpath(self):
        """ return path on disk """
        return pbxpath.realpath(self.project(), self.abspath())

    def displayname(self):
        """ return the name to displayed """
        name = getattr(self, u'pbx_name', None)
        if name is None:
            name = getattr(self, u'pbx_path', None)
        return name

    def comment(self):
        """ override """
        return self.displayname()

    def _validate(self):
        resolved, issues = super(PBXFileReference, self)._validate()
        if self.pbx_sourceTree is None:
            issues.append(u'{0} invalid sourceTree: {1}'.format(self, self.pbx_sourceTree))
        elif not func.isstr(self.pbx_name) and not func.isstr(self.pbx_path):
            issues.append(u'{0} invalid name / path.'.format(self))
        elif not func.isstr(self.pbx_explicitFileType) and not func.isstr(self.pbx_lastKnownFileType):
            issues.append(u'{0} invalid explicitFileType / lastKnownFileType.'.format(self))
        return resolved, issues


class PBXReferenceProxy(baseobject.PBXBaseObject):
    """
    owner: PBXGroup
    relative: one[group] to many[refproxy]

    pbx-attr:
        fileType        str, nullable
        path            str, nullable
        remoteRef       PBXContainerItemProxy, nonnull
        sourceTree      str, nonnull, default 'BUILT_PRODUCTS_DIR'  
    """
    def __init__(self, xcproj, guid):
        super(PBXReferenceProxy, self).__init__(xcproj, guid)
        self.pbx_sourceTree = pbxconsts.SOURCE_TREE.BUILT_PRODUCTS_DIR # str
        # other attributes
        self.__abspath = None # str : $(SRCROOT)/path/to/file
        # self.realpath = None # str : real path on dick

    def __setattr__(self, name, value):
        if name == u'pbx_remoteRef':
            pbxhelper.pbxobj_set_pbxobj_attr(self, PBXReferenceProxy, name, value, \
                self.is_valid_ref )
        elif name == u'pbx_path':
            pbxpath.set_group_file_path(self, PBXReferenceProxy, value)
        else:
            super(PBXReferenceProxy, self).__setattr__(name, value)

    def is_valid_ref(self, obj):
        return isinstance(obj, baseobject.PBXBaseObject) and obj.isa == 'PBXContainerItemProxy'

    def displayname(self):
        """ return the name to displayed """
        name = getattr(self, u'pbx_name', None)
        if name is None:
            name = getattr(self, u'pbx_path', None)
        return name

    def _accepted_owner(self, obj):
        """ override """
        from xcodeproj.pbxproj.objects import group
        return isinstance(obj, group.PBXGroup) and obj.haschild(self)

    def comment(self):
        """ override """
        return self.displayname()

    def abspath(self):
        """ return path in project """
        if self.__abspath is None:
            self.__abspath = pbxpath.abspath(self)
        return self.__abspath

    def realpath(self):
        """ return path on disk """
        return pbxpath.realpath(self.project(), self.abspath())

    def filetype(self):
        return self.pbx_fileType

    def allow_multi_owners(self):
        return False

    def _validate(self):
        pbxhelper.pbxobj_validate_pbxobj_attr(self, u'pbx_remoteRef', throw_exception=True)
        return super(PBXReferenceProxy, self)._validate()
