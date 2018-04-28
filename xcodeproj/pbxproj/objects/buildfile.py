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
from xcodeproj.pbxproj import attr
from xcodeproj.utils import func

class PBXBuildFile(baseobject.PBXBaseObject):
    """
    Build Settings for PBXFileReference

    owner:    PBXBuildPhase
    relative:    one[buildphase] to many[buildfile]

    pbx-attr:
        fileRef         allow_fileref_types(), nonnull
        settings        dict, nullable
    """
    @staticmethod
    def new_buildfile(fileref, **kwargs): # kwargs:settings
        obj = fileref.project().new_object(u'PBXBuildFile')
        obj.pbx_fileRef = fileref
        if u'settings' in kwargs:
            obj.pbx_settings = kwargs[u'settings']
        return obj


    def __setattr__(self, name, value):
        if name == u'pbx_fileRef':
            pbxhelper.pbxobj_set_pbxobj_attr(self, PBXBuildFile, name, value, self.is_valid_fileref)
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

    def _validate(self):
        pbxhelper.pbxobj_validate_pbxobj_attr(self, u'pbx_fileRef', throw_exception=True)
        return super(PBXBuildFile, self)._validate()

    def displayname(self):
        return self.pbx_fileRef.displayname() if not self.pbx_fileRef is None else None

    def comment(self):
        """ override """
        refcomment = None
        parentcomment = None

        if not self.pbx_fileRef is None:
            refcomment = self.pbx_fileRef.comment()

        owner = func.get_list_item(self.owners().values(), 0)
        if not owner is None:
            parentcomment = owner.comment()

        comment = u'{ref} in {parent}'.format(\
            ref=unicode(refcomment) if not refcomment is None else u'(null)', \
            parent=unicode(parentcomment) if not parentcomment is None else u'(null)')
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

    def filetype(self):
        """ return filetype of buildfile's file reference """
        if not self.pbx_fileRef is None \
            and self.pbx_fileRef.isa in [u'PBXFileReference', u'PBXReferenceProxy']:
            return self.pbx_fileRef.filetype()
        return None

    def equalto(self, other):
        """ override """
        if isinstance(other, PBXBuildFile):
            if self.pbx_fileRef is None and other.pbx_fileRef is None:
                return self.guid == other.guid
            elif not self.pbx_fileRef is None and not other.pbx_fileRef is None:
                return self.pbx_fileRef.equalto(other.pbx_fileRef)
        return False



