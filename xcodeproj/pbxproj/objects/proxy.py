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


class PBXContainerItemProxy(baseobject.PBXBaseObject):
    """
    owner:    PBXTargetDependency / PBXReferenceProxy
    relative:    one to one

    pbx-attr:
        containerPortal         PBXProject/PBXFileReference, nonnull
        proxyType               int, nonnull, default 0
        remoteGlobalIDString    guid, nonnull
        remoteInfo              str, nullable
    """

    def __init__(self, xcproj, guid):
        super(PBXContainerItemProxy, self).__init__(xcproj, guid)
        self.pbx_proxyType = 0 # int

    def __setattr__(self, name, value):
        if name == u'pbx_containerPortal':
            pbxhelper.set_pbxobj_value(self, PBXContainerItemProxy, name, value, \
                lambda o: isinstance(o, baseobject.PBXBaseObject)\
                and o.isa in [u'PBXProject', u'PBXFileReference'])
        elif name == u'pbx_remoteGlobalIDString':
            if isinstance(value, baseobject.PBXBaseObject):
                value = value.guid
            super(PBXContainerItemProxy, self).__setattr__(name, value)
        else:
            super(PBXContainerItemProxy, self).__setattr__(name, value)

    def _accepted_owner(self, obj):
        if not isinstance(obj, baseobject.PBXBaseObject):
            return False
        if obj.isa == u'PBXTargetDependency' and self == obj.pbx_targetProxy:
            return True
        if obj.isa == u'PBXReferenceProxy' and self == obu.pbx_remoteRef:
            return True
        return False

    def duplicate(self):
        """ override """
        obj = super(PBXContainerItemProxy, self).duplicate()
        for attr, val in self.__dict__.items():
            if func.hasprefix(attr, pbxconsts.PBX_ATTR_PREFIX):
                setattr(obj, attr, val)
        return obj

    def comment(self):
        """ override """
        return self.isa

    def allow_multi_owners(self):
        return False

    def _validate(self):
        if self.pbx_containerPortal != self._xcproj.pbx_rootObject:
            pbxhelper.validate_dependent_object(self, u'pbx_containerPortal', throw_exception=True)
        return super(PBXContainerItemProxy, self)._validate()

