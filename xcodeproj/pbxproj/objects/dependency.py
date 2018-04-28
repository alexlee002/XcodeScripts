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
            pbxhelper.pbxobj_set_pbxobj_attr(self, PBXTargetDependency, name, value, \
                self.is_valid_target_proxy)
        elif name == u'pbx_target':
            pbxhelper.pbxobj_set_pbxobj_attr(self, PBXTargetDependency, name, value, \
                self.is_valid_target)
        else:
            super(PBXTargetDependency, self).__setattr__(name, value)

    def is_valid_target_proxy(self, obj):
        """ attr validator """
        return isinstance(obj, baseobject.PBXBaseObject) and obj.isa == u'PBXContainerItemProxy'

    def is_valid_target(self, obj):
        """ attr validator """
        from xcodeproj.pbxproj.objects import target
        return isinstance(obj, target.PBXTarget)

    def comment(self):
        """ override """
        return self.isa

    def _accepted_owner(self, obj):
        """ override """
        from xcodeproj.pbxproj.objects import target
        return isinstance(obj, target.PBXTarget) and obj.depends(self)

    def allow_multi_owners(self):
        """ override """
        return False

    def _duplicate_attr(self, attr, val):
        if attr == u'pbx_targetProxy':
            self.pbx_targetProxy = val.duplicate()

    def _validate(self):
        pbxhelper.pbxobj_validate_pbxobj_attr(self, u'pbx_targetProxy', throw_exception=True)
        if not self.pbx_target is None:
            pbxhelper.pbxobj_validate_pbxobj_attr(self, u'pbx_target', throw_exception=True)
        return super(PBXTargetDependency, self)._validate()
