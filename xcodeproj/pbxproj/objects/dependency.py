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


class PBXTargetDependency(baseobject.PBXBaseObject):
    """
    owners: PBXNativeTarget
    relative: one to one

    pbx-attr:
        name            str, nullable
        targetProxy     PBXContainerItemProxy, nonnull
        target          PBXTarget,  nullable
    """

    def __setattr__(self, name, value): 
        if name == u'pbx_targetProxy':
            pbxhelper.set_pbxobj_value(self, PBXTargetDependency, name, value, \
                lambda o:isinstance(o, baseobject.PBXBaseObject) \
                and o.isa == u'PBXContainerItemProxy')
        elif name == u'pbx_target':
            from xcodeproj.pbxproj.objects import target
            pbxhelper.set_pbxobj_value(self, PBXTargetDependency, name, value, \
                lambda o:isinstance(o, target.PBXTarget))
        else:
            super(PBXTargetDependency, self).__setattr__(name, value)

    def comment(self):
        """ override """
        return self.isa

    def duplicate(self):
        """ override """
        obj = super(PBXTargetDependency, self).duplicate()
        for attr, val in self.__dict__.items():
            if func.hasprefix(attr, pbxconsts.PBX_ATTR_PREFIX):
                setattr(obj, attr, val)
        return obj

    def _accepted_owner(self, obj):
        """ override """
        from xcodeproj.pbxproj.objects import target
        return isinstance(obj, target.PBXTarget) and obj.depends(self)

    def allow_multi_owners(self):
        """ override """
        return False

    def _validate(self):
        pbxhelper.validate_dependent_object(self, u'pbx_targetProxy', throw_exception=True)
        return super(PBXTargetDependency, self)._validate()
