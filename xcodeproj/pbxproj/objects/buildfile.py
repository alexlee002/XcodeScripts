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
from xcodeproj.pbxproj import pbxhelper
from xcodeproj.utils import func

class PBXBuildFile(baseobject.PBXBaseObject):
    """
    Build Settings for PBXFileReference

    owner:    PBXBuildPhase
    relative:    one[buildphase] to many[buildfile]

    pbx-attr:
        fileRef         allow_fileref_types(), nonnull
        Settings        dict, nullable
    """

    def __setattr__(self, name, value):
        if name == u'pbx_fileRef':
            pbxhelper.set_pbxobj_value(self, PBXBuildFile, name, value, self.is_valid_fileref)
        elif name == u'pbx_settings':
            self.__set_settings(value)
        else:
            super(PBXBuildFile, self).__setattr__(name, value)

    def __set_settings(self, value):
        if value is None or func.isdict(value):
            super(PBXBuildFile, self).__setattr__(u'pbx_settings', value)
        else:
            logger.error(u'[PBXBuildFile] illegal settings:{0}'.format(obj))


    def allow_fileref_types(self):
        """ fileRef types """
        return [u'PBXFileReference', u'PBXReferenceProxy', u'PBXVariantGroup']

    def is_valid_fileref(self, fileref):
        """ veridate type of fileRefObj """
        return isinstance(fileref, baseobject.PBXBaseObject) \
            and fileref.isa in self.allow_fileref_types()

    def _print_in_one_line(self):
        return True

    def duplicate(self):
        """ override """
        obj = super(PBXBuildFile, self).duplicate()
        obj.pbx_fileRef = self.pbx_fileRef
        obj.pbx_settings = self.pbx_settings
        return obj

    def _validate(self):
        pbxhelper.validate_dependent_object(self, u'pbx_fileRef', throw_exception=True)
        return super(PBXBuildFile, self)._validate()

    def comment(self):
        """ override """
        refcomment = None
        parentcomment = None

        if not self.pbx_fileRef is None:
            refcomment = self.pbx_fileRef.comment()
        owner = func.get_list_item(self.owners(), 0)
        if not owner is None:
            parentcomment = owner.comment()

        comment = u'{ref} in {parent}'.format(\
            ref=(refcomment if not refcomment is None else u'(null)'), \
            parent=(parentcomment if not parentcomment is None else u'(null)'))
        return comment

    def _accepted_owner(self, obj):
        from xcodeproj.pbxproj.objects import buildphase
        return isinstance(obj, buildphase.PBXBuildPhase) and obj.hasfile(self)

    def allow_multi_owners(self):
        """ override """
        return False

    def abspath(self):
        """ return path in project """
        obj = getattr(self, u'pbx_fileRef', None)
        if not obj is None:
            return obj.abspath()
        return None

    def realpath(self):
        """ return path on disk """
        obj = getattr(self, u'pbx_fileRef', None)
        if not obj is None:
            return obj.realpath()
        return None






