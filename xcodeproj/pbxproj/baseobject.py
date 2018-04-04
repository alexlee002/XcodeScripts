#!/usr/bin/python
# encoding:utf-8
# 
# copyright (c) Alex Lee, All rights reserved.

class PBXValidationError(Exception):
    pass

import os
import sys
ModuleRoot = os.path.abspath(os.path.join(__file__, '../../..'))
if os.path.isdir(ModuleRoot) and not ModuleRoot in sys.path:
    sys.path.append(ModuleRoot)

from xcodeproj.utils import func
from xcodeproj.utils import logger
from xcodeproj.pbxproj import pbxhelper
from xcodeproj.pbxproj import abstract
from xcodeproj.pbxproj import pbxconsts


class PBXBaseObject(abstract.PBXAbstract):
    
    def __init__(self, xcproj, guid):
        super(PBXBaseObject, self).__init__()
        self.guid = guid

        self._xcproj = xcproj

        self.__referrers = {} # {guid: referrer}
        self.__owners = None # {guid: owner}
        self.__dirty = True

    def __getattribute__(self, name):
        if name == u'isa':
            return self.__class__.__name__
        else:
            return super(PBXBaseObject, self).__getattribute__(name)

    def __setattr__(self, name, value):
        if func.hasprefix(name, pbxconsts.PBX_ATTR_PREFIX):
            super(PBXBaseObject, self).__setattr__(name, value)
            self.__dirty = True
        else:
            super(PBXBaseObject, self).__setattr__(name, value)

    def __str__(self):
        if self.guid or self.isa:
            return '{guid}({isa})'.format(isa=self.isa, guid=self.guid)
        return super(PBXBaseObject, self).__str__()

    def __repr__(self):
        if self.guid or self.isa:
            return u'{guid}({isa})'.format(isa=self.isa, guid=self.guid)
        return super(PBXBaseObject, self).__repr__()

    def referrers(self):
        """ 
        return {guid: object}, that the value object referred to 'self'
        eg:
            PBXBuildFile.fileRef = PBXFileReference
            so,
            PBXFileReference.referrs contains PBXBuildFile
        """
        return self.__referrers if not self.__referrers is None else {}

    def add_referrer(self, obj):
        """
        mark up that 'obj' referred to self
        """
        if isinstance(obj, PBXBaseObject):
            self._xcproj.add_object(obj)
            self.__referrers[obj.guid] = obj
        elif func.isstr(obj):
            referrer = self._xcproj.get_object(obj)
            if not referrer is None:
                self.__referrers[referrer.guid] = referrer
            else:
                raise ValueError(u'[XcodeProj] object not found:{0}'.format(obj))
        self.__owners = None # need to re-caculate owners

    def remove_referrer(self, obj):
        """
        mark up that 'obj' no longer referred to self
        """
        guid = None
        if isinstance(obj, PBXBaseObject):
            guid = obj.guid
        elif func.isstr(obj):
            guid = unicode(obj)

        self.__referrers.pop(guid, None)
        if len(self.__referrers) == 0:
            self._xcproj.remove_object(self)
        self.__owners = None # need to re-caculate owners

    def comment(self):
        """ xcode pbxproj comment """
        return None

    def allow_multi_owners(self):
        """ """
        return False

    def owners(self):
        """ """
        if self.__owners is None:
            self.__owners = [ref for ref in self.referrers().values() if self._accepted_owner(ref)]
        return self.__owners

    def _accepted_owner(self, obj):
        return False

    def hasowner(self, owner):
        """ """
        if isinstance(owner, PBXBaseObject):
            return owner.guid in self.owners
        elif bpxhelper.is_valid_guid(owner):
            return owner in self.owners
        return False

    def has_multi_owners(self):
        """ """
        return len(self.owner()) > 1

    def duplicate(self):
        return self._xcproj.new_object(self.isa)

    def pbxdict(self):
        """ override """
        dic = super(PBXBaseObject, self).pbxdict()
        dic[u'isa'] = self.isa
        return dic

    def validate(self):
        """ validate the object """
        if self.isdirty():
            resolved, issues = self._validate()
            self.__dirty = False

            if len(resolved) > 0:
                logger.verbose('========= {0} ========='.format(self))
                for item in resolved:
                    logger.verbose(item)
                logger.verbose('')

            if len(issues) > 0:
                logger.warn('========= {0} ========='.format(self))
                for item in issues:
                    logger.warn(item)
                logger.verbose('')

    def _validate(self):
        resolved = []
        issues = []

        if not pbxhelper.is_valid_guid(self.guid):
            issues.append('illegal guid:{guid}.'.format(self.guid))
        return resolved, issues

    def markdirty(self):
        """ mark up that the object has changed and need validate """
        self.__dirty = True

    def isdirty(self):
        """ return True if the object has changed since last validation """
        return self.__dirty


