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
from xcodeproj.utils import func


class PBXTarget(baseobject.PBXBaseObject):
    """
    owner:    PBXProject
    relative: one[project] to many[target]

    pbx-attr: 
        buildConfigurationList      XCConfigurationList, nonnull
        buildPhases                 [@is_valid_build_phase], nonnull, default []
        dependencies                [@is_valid_dependency], nonnull, default []
        name                        str, nonnull
        productName                 str, nonnull
    """
    def __init__(self, xcproj, guid):
        super(PBXTarget, self).__init__(xcproj, guid)
        self.pbx_buildPhases = [] # [guid]
        self.pbx_dependencies = [] # [guid]

    def __setattr__(self, name, value):
        if name == u'pbx_buildConfigurationList':
            pbxhelper.set_pbxobj_value(self, PBXTarget, name, value, \
                lambda o:isinstance(o, baseobject.PBXBaseObject) and o.isa == 'XCConfigurationList')
        elif name == u'pbx_buildPhases':
            pbxhelper.set_pbxobj_list_value(self, PBXTarget, name, value, self.is_valid_build_phase)
        elif name == u'pbx_dependencies':
            pbxhelper.set_pbxobj_list_value(self, PBXTarget, name, value, self.is_valid_dependency)
        else:
            super(PBXTarget, self).__setattr__(name, value)

    def displayname(self):
        """ return name to be displayed """
        return self.pbx_name

    def _accepted_owner(self, obj):
        """ override """
        return isinstance(obj, baseobject.PBXBaseObject) \
            and obj.isa == 'PBXProject' and obj.hastarget(self)

    def duplicate(self):
        """ override """
        obj = super(PBXContainerItemProxy, self).duplicate()
        for attr, val in self.__dict__.items():
            if attr == u'pbx_buildPhases':
                for bp in val:
                    obj.add_build_pahse(bp.duplicate())
            if attr == u'pbx_name':
                obj.pbx_name = u'{name} copy'.format(self.pbx_name)
            if func.hasprefix(attr, pbxconsts.PBX_ATTR_PREFIX):
                setattr(obj, attr, val)
        return obj

    def comment(self):
        """ override """
        return self.pbx_name

    def is_valid_build_phase(self, phase):
        from xcodeproj.pbxproj.objects import buildphase
        return isinstance(phase, buildphase.PBXBuildPhase)

    def is_valid_dependency(self, dep):
        return isinstance(dep, baseobject.PBXBaseObject) and dep.isa == u'PBXTargetDependency'

    def has_build_phase(self, pahse):
        return pbxhelper.pbxobj_has_list_value(self, u'pbx_buildPhases', phase, \
            self.is_valid_build_phase)

    def add_build_pahse(self, phase, index=None):
        pbxhelper.pbxobj_add_list_value(self, u'pbx_buildPhases', phase, \
            self.is_valid_build_phase, index=index)

    def remove_build_phase(self, phase):
        pbxhelper.pbxobj_remove_list_value(self, u'pbx_buildPhases', phase, \
            self.is_valid_build_phase)

    def has_dependency(self, dep):
        return pbxhelper.pbxobj_has_list_value(self, u'pbx_dependencies', dep, \
            self.is_valid_dependency)

    def add_dependency(self, dep, index=None):
        pbxhelper.pbxobj_add_list_value(self, u'pbx_dependencies', dep, \
            self.is_valid_dependency, index=index)

    def remove_dependency(self, dep):
        pbxhelper.pbxobj_remove_list_value(self, u'pbx_dependencies', dep, \
            self.is_valid_dependency)

    def __validate_dependencies(self, resolved, issues):
        for dep in self.pbx_dependencies:
            try:
                dep.validate()
            except Exception as e:
                if dep is None or isinstance(e, baseobject.PBXValidationError):
                    self.remove_dependency(dep)
                    resolved.append(\
                        u'remove invalid dependency {dep}, reason:{e}'.format(dep=dep, e=e))
                else:
                    raise

    def __validate_build_phases(self, resolved, issues):
        bpdict = dict()
        for bp in self.pbx_buildPhases:
            try:
                bp.validate()
            except Exception as e:
                if bp is None or isinstance(e, baseobject.PBXValidationError):
                    self.remove_build_phase(bp)
                    resolved.append(\
                        u'remove invalid build phase {bp}; reason: {e}'.format(bp=bp, e=e))
                    continue
                else:
                    raise

            if bp.isa in ['PBXHeadersBuildPhase', 'PBXSourcesBuildPhase', \
                    'PBXFrameworksBuildPhase', 'PBXResourcesBuildPhase']:
                if not bp.isa in bpdict:
                    bpdict[bp.isa] = [bp]
                else:
                    bpdict[bp.isa].append(bp)

        for isa, bplist in bpdict.items():
            if len(bplist) > 1:
                reserved = bplist[0]
                for bp in bplist[1:]:
                    for bf in bp.pbx_files:
                        reserved.addfile(bf)
                        bp.removefile(bf)
                self.remove_build_phase(bp)
                resolve.append(u'merge {0} to {1}'.format(bp, reserved))

    def _validate(self):
        resolved, issues = super(PBXTarget, self)._validate()
        pbxhelper.validate_dependent_object(self, u'pbx_buildConfigurationList', issues=issues)

        self.__validate_dependencies(resolved, issues)
        self.__validate_build_phases(resolved, issues)
        return resolved, issues

        
class PBXNativeTarget(PBXTarget):
    """
    pbx-attr:
        buildRules          [], nonnull, default []
        productReference    PBXFileReference, nonnull
        productType         str, nonnull
    """
    def __init__(self, xcproj, guid):
        super(PBXNativeTarget, self).__init__(xcproj, guid)
        self.pbx_buildRules = [] # []

    def __setattr__(self, name, value):
        if name == 'pbx_productReference':
            pbxhelper.set_pbxobj_value(self, PBXNativeTarget, name, value, \
                lambda o:isinstance(o, baseobject.PBXBaseObject) and o.isa == 'PBXFileReference')
        else:
            super(PBXNativeTarget, self).__setattr__(name, value)


class PBXAggregateTarget(PBXTarget):
    pass











