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

SINGLE_PHASES = (
    u'PBXHeadersBuildPhase', 
    u'PBXSourcesBuildPhase', 
    u'PBXFrameworksBuildPhase', 
    u'PBXResourcesBuildPhase'
)

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
            pbxhelper.pbxobj_set_pbxobj_attr(self, PBXTarget, name, value, \
                lambda o:isinstance(o, baseobject.PBXBaseObject) and o.isa == u'XCConfigurationList')
        elif name == u'pbx_buildPhases':
            pbxhelper.pbxobj_set_pbxlist_attr(self, PBXTarget, name, value, self.is_valid_build_phase)
        elif name == u'pbx_dependencies':
            pbxhelper.pbxobj_set_pbxlist_attr(self, PBXTarget, name, value, self.is_valid_dependency)
        else:
            super(PBXTarget, self).__setattr__(name, value)

    def displayname(self):
        """ return name to be displayed """
        return self.pbx_name

    def _accepted_owner(self, obj):
        """ override """
        return isinstance(obj, baseobject.PBXBaseObject) \
            and obj.isa == u'PBXProject' and obj.hastarget(self)

    def _duplicate_attr(self, attr, val):
        if attr == u'pbx_buildPhases':
            for bp in val:
                obj.add_build_pahse(bp.duplicate())
        elif attr == u'pbx_name':
            obj.pbx_name = u'{name} copy'.format(self.pbx_name)
        else:
            super(PBXTarget, self)._duplicate_attr(attr, val)

    def comment(self):
        """ override """
        return self.pbx_name

    def is_valid_build_phase(self, phase):
        """ check if phase is valid """
        from xcodeproj.pbxproj.objects import buildphase
        return isinstance(phase, buildphase.PBXBuildPhase)

    def is_valid_dependency(self, dep):
        """ check if dep is valid dependency """
        return isinstance(dep, baseobject.PBXBaseObject) and dep.isa == u'PBXTargetDependency'

    def has_build_phase(self, pahse):
        """ check if build phase exists """
        return pbxhelper.pbxobj_has_pbxlist_value(self, u'pbx_buildPhases', phase, \
            self.is_valid_build_phase)

    def add_build_phase(self, phase, index=None):
        """ add build phase """
        pbxhelper.pbxobj_add_pbxlist_value(self, u'pbx_buildPhases', phase, \
            self.is_valid_build_phase, index=index)

    def get_build_phase(self, isa, name=None, create=False):
        """ get build phase, create a new one if not exists """
        def __cmp(phase):
            if phase.isa == isa:
                return True if name is None else phase.displayname() == name
            return False

        bp = func.get_list_item(func.take(lambda o:__cmp(o), self.pbx_buildPhases), 0)
        if bp is None and create:
            bp = self.create_build_phase(isa, name)
        return bp

    def create_build_phase(self, isa, name=None):
        """ create new build phase """
        phase = self.project().new_object(isa)
        if not name is None:
            phase.pbx_name = name
        elif isa in [u'PBXCopyFilesBuildPhase', u'PBXShellScriptBuildPhase']:
            phase.pbx_name = self.__gen_build_phase_name(isa, phase.displayname())
        self.add_build_phase(phase)
        return phase

    def __gen_build_phase_name(self, isa, name):
        names = [o.displayname() for o in self.pbx_buildPhases if isa == o.isa]
        for num in xrange(1,100):
            new_name = u'{name} {num}'.format(name=name, num=num)
            if not new_name in names:
                return new_name
        return name

    def remove_build_phase(self, phase):
        """ remove build phase """
        pbxhelper.pbxobj_remove_pbxlist_value(self, u'pbx_buildPhases', phase, \
            self.is_valid_build_phase)

    def has_dependency(self, dep):
        """ check if dependency exists """
        return pbxhelper.pbxobj_has_pbxlist_value(self, u'pbx_dependencies', dep, \
            self.is_valid_dependency)

    def add_dependency(self, dep, index=None):
        """ add dependency """
        pbxhelper.pbxobj_add_pbxlist_value(self, u'pbx_dependencies', dep, \
            self.is_valid_dependency, index=index)

    def remove_dependency(self, dep):
        """ remove dependency """
        pbxhelper.pbxobj_remove_pbxlist_value(self, u'pbx_dependencies', dep, \
            self.is_valid_dependency)

    def getconfig(self, name, auto_create=False):
        """ return buildconfiguration with name or None """
        if self.pbx_buildConfigurationList is None:
            if not auto_create:
                return None
            else:
                self.pbx_buildConfigurationList = self.project().new_object(u'XCConfigurationList')

        return self.pbx_buildConfigurationList.getconfig(name, auto_create)

    def configurations(self):
        """ return all buildconfigurations or None if pbx_buildConfigurationList is None """
        if self.pbx_buildConfigurationList is None:
            return None
        return self.pbx_buildConfigurationList.pbx_buildConfigurations

    def __validate_dependencies(self, resolved, issues):
        pbxhelper.pbxobj_validate_pbxlist_attr(self, u'pbx_dependencies', \
            self.is_valid_dependency, resolved=resolved, issues=issues)

    def __validate_build_phases(self, resolved, issues):
        pbxhelper.pbxobj_validate_pbxlist_attr(self, u'pbx_buildPhases', \
            self.is_valid_dependency, resolved=resolved, issues=issues)

        def __phase_key(phase):
            return phase.isa if phase.isa in SINGLE_PHASES else phase.guid

        def __deduplicate_phase(reserved, delphase):
            for bf in delphase.pbx_files:
                reserved.addfile(bf)
                delphase.removefile(bf)
            self.remove_build_phase(delphase)
            reserved.replace(delphase)

        pbxhelper.pbxobj_deduplicate_pbxlist_value(self, u'pbx_buildPhases', \
            __phase_key, __deduplicate_phase, resolved, issues)

    def _validate(self):
        resolved, issues = super(PBXTarget, self)._validate()
        pbxhelper.pbxobj_validate_pbxobj_attr(self, u'pbx_buildConfigurationList', issues=issues)

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
            pbxhelper.pbxobj_set_pbxobj_attr(self, PBXNativeTarget, name, value, \
                lambda o:isinstance(o, baseobject.PBXBaseObject) and o.isa == 'PBXFileReference')
        else:
            super(PBXNativeTarget, self).__setattr__(name, value)


class PBXAggregateTarget(PBXTarget):
    pass











