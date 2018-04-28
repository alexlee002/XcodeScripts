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
from xcodeproj.pbxproj import pbxconsts
from xcodeproj.utils import func
from xcodeproj.utils import logger


class PBXProject(baseobject.PBXBaseObject): 
    """
    pbx-attr:
        attributes              dict, nonnull, default {}
        buildConfigurationList  XCConfigurationList, nonnull
        compatibilityVersion    str, nullable
        developmentRegion       str, nullable, default 'English'
        hasScannedForEncodings  int, nullable, default 0
        knownRegions            [str], nonnull, default []
        mainGroup               PBXGroup, nonnull
        productRefGroup         PBXGroup, nonnull
        projectDirPath          str, nonnull, default ''
        projectReferences       [dict()], nullable
        projectRoot             str, nullable, default ''
        targets                 [PBXTarget], nonnull, default []
    """

    def __init__(self, xcproj, guid):
        super(PBXProject, self).__init__(xcproj, guid)
        # pbx attributes
        self.pbx_attributes = dict()
        self.pbx_developmentRegion = u'English' # str
        self.pbx_hasScannedForEncodings = 0 # int
        self.pbx_knownRegions = [] # [str]
        self.pbx_projectDirPath = u'' # str
        self.pbx_projectRoot = u'' # str
        self.pbx_targets = [] # [guid]

    def __setattr__(self, name, value):
        if name == u'pbx_buildConfigurationList':
            pbxhelper.pbxobj_set_pbxobj_attr(self, PBXProject, name, value, \
                lambda o:isinstance(o, baseobject.PBXBaseObject) and o.isa == 'XCConfigurationList')

        elif name in [u'pbx_mainGroup', u'pbx_productRefGroup']:
            pbxhelper.pbxobj_set_pbxobj_attr(self, PBXProject, name, value, \
                lambda o:isinstance(o, baseobject.PBXBaseObject) and o.isa == 'PBXGroup')

        elif name == u'pbx_targets':
            pbxhelper.pbxobj_set_pbxlist_attr(self, PBXProject, name, value, self.is_valid_target)

        elif name == u'pbx_projectReferences':
            self.__set_project_references(value)

        elif name == u'pbx_attributes':
            if not func.isdict(value):
                value = dict()
            super(PBXProject, self).__setattr__(name, value)

        elif name == u'pbx_knownRegions':
            if not func.isseq(value):
                value = [value]
            super(PBXProject, self).__setattr__(name, value)

        else:
            super(PBXProject, self).__setattr__(name, value)

    def __set_project_references(self, value):
        if not func.isseq(value):
            return

        value, rejects = func.filter_items(self.is_valid_project_reference, value)
        if len(rejects) > 0:
            logger.warn(u'{0} ignore invalid project reference:\n\t{1}'\
                .format(self, u'\n\t'.join(map(lambda o: str(o), rejects))))

        super(PBXProject, self).__setattr__(u'pbx_projectReferences', value)

    def is_valid_project_reference(self, value):
        """ check if value is valid project reference """
        if not func.isdict(value):
            return False

        obj = value.get(u'ProductGroup')
        if not isinstance(obj, baseobject.PBXBaseObject) or not obj.isa == u'PBXGroup':
            return False

        obj = value.get(u'ProjectRef')
        if not isinstance(obj, baseobject.PBXBaseObject) or not obj.isa == u'PBXFileReference':
            return False

        return True

    def is_valid_target(self, obj):
        """ check if obj is valid target object """
        from xcodeproj.pbxproj.objects import target
        return isinstance(obj, target.PBXTarget)

    def has_project_reference(self, projref):
        """ return True if project reference is existed """
        if not self.is_valid_project_reference(projref):
            return False

        proj_refs = self.pbx_projectReferences
        if proj_refs is None:
            return False

        for ref in proj_refs:
            if ref[u'ProductGroup'].guid == projref[u'ProductGroup'].guid \
                and ref[u'ProjectRef'].guid == projref[u'ProjectRef'].guid:
                return True
        return False

    def add_project_reference(self, projref):
        """ add project reference """
        if self.has_project_reference(projref):
            return

        proj_refs = self.pbx_projectReferences
        if proj_refs is None:
            proj_refs = [projref]
        else:
            proj_refs.append(projref)

        projref[u'ProductGroup'].add_referrer(self, u'pbx_projectReferences.ProductGroup')
        projref[u'ProjectRef'].add_referrer(self, u'pbx_projectReferences.ProjectRef')

    def remove_project_reference(self, projref):
        """ remove project reference """
        if not self.is_valid_project_reference(projref):
            return

        proj_refs = self.pbx_projectReferences
        if proj_refs is None:
            return

        idx = 0
        while idx < len(proj_refs):
            ref = proj_refs[idx]
            if ref[u'ProductGroup'].guid == projref[u'ProductGroup'].guid \
                and ref[u'ProjectRef'].guid == projref[u'ProjectRef'].guid:
                
                proj_refs.pop(idx)
                ref[u'ProductGroup'].remove_referrer(self)
                ref[u'ProjectRef'].remove_referrer(self)
            else:
                idx += 1

    def hastarget(self, target):
        """
        return True if contains target 
        :param  target   guid or target object
        """
        return pbxhelper.pbxobj_has_pbxlist_value(self, u'pbx_targets', target, \
            self.is_valid_target)

    def __new_target(self, isa, name):
        def __gen_target_name(name):
            names = set([o.displayname() for o in self.pbx_targets])
            new_name = name
            idx = 1
            while new_name in names:
                new_name = u'{name}-{idx}'.format(name=name, idx=idx)
                idx += 1
            return new_name

        target = self.gettarget(name)
        if not target is None:
            if not target.pbx_productType == product_type or not target.isa == isa:
                target = None
                name = __gen_target_name(name)

        new_create = False
        if target is None:
            target = self.project().new_object(isa)
            target.pbx_name = name
            from xcodeproj.pbxproj import projhelper
            self.addtarget(target)
            new_create = True
        return target, new_create

    def new_native_target(self, name, product_type=pbxconsts.TARGET_PRODUCT_TYPE.app, \
        platform=pbxconsts.PLATFORM.ios, language=pbxconsts.LANGUAGE.objc, deployment_target=None):
        """
        add native target named 'name'
        if an target with the same name, same isa, same product type, return the exists.
        if the target name confilict with existed targets, add number subfix to the name
        """
        target, new_create = self.__new_target(u'PBXNativeTarget', name)
        if target.pbx_productType is None:
            target.pbx_productType = product_type
        if target.pbx_productName is None:
            target.pbx_productName = name

        if new_create:
            from xcodeproj.pbxproj import projhelper
            target.pbx_buildConfigurationList = projhelper.default_target_configuration_list(\
                self.project(), platform=platform, product_type=product_type, language=language, \
                deployment_target=deployment_target)
            target.create_build_phase(u'PBXSourcesBuildPhase')
            target.create_build_phase(u'PBXFrameworksBuildPhase')
            target.create_build_phase(u'PBXResourcesBuildPhase')
        return target

    def gettarget(self, name):
        return func.get_list_item(func.take(lambda o:o.pbx_name == name, self.pbx_targets), 0)

    def addtarget(self, target, index=None):
        """ add target to this project """
        pbxhelper.pbxobj_add_pbxlist_value(self, u'pbx_targets', target, self.is_valid_target, \
            index=index)

    def removetarget(self, target):
        """ 
        remove target 
        :param target    target object or guid to be removed
        """
        pbxhelper.pbxobj_remove_pbxlist_value(self, u'pbx_targets', target, self.is_valid_target)

    def abspath(self):
        """ return abspath in project """
        return u'$(SRCROOT)' #self._xcproj.project_dir()

    def realpath(self):
        """ return path in disk """
        return self.project().project_dir()

    def displayname(self):
        """ the name of self """
        return self.project().project_name()

    def comment(self):
        """ override """
        return u'Project object'

    def __validate_project_references(self, resolved, issues):
        prodrefs = self.pbx_projectReferences
        if not prodrefs is None:
            if not func.isseq(prodrefs):
                issues.append(u'illegal projectReferences: {ref}'.format(ref=prodrefs))
            else:
                for refdict in list(prodrefs):
                    if not self.is_valid_project_reference(refdict):
                        prodrefs.remove(refdict)
                        for obj in [refdict.get(u'ProductGroup'), refdict.get(u'ProjectRef')]:
                            if not obj is None:
                                obj.remove_referrer(self)
                        issues.append(u'remove invalid projectReference:{ref}'.format(ref=refdict))
                        continue

                    for obj in [refdict.get(u'ProductGroup'), refdict.get(u'ProjectRef')]:
                        try:
                            obj.validate()
                        except baseobject.PBXValidationError as e:
                            self.remove_project_reference(refdict)
                            resolved.append(u'remove invalid projectReference:{ref}; {ex}'\
                                .format(ref=obj, ex=e))

    def __deduplicate_project_reference(self, resolved=[], issues=[]):
        def __group_key(obj):
            return obj[u'ProjectRef'].realpath()

        def __deduplicate_action(reserved, delref):
            reserved_ref_group = reserved[u'ProductGroup']
            for ch in delref[u'ProductGroup'].pbx_children:
                reserved_ref_group.addchild(ch, move=True)
            bakup = dict(reserved)
            self.remove_project_reference(delref)
            for k, v in bakup.items():
                reserved[k] = v
                v.add_referrer(self, u'pbx_projectReferences.{k}'.format(k=k))

        pbxhelper.pbxobj_deduplicate_pbxlist_value(self, u'pbx_projectReferences', \
            __group_key, __deduplicate_action, resolved, issues)

    def _validate(self):
        resolved, issues = super(PBXProject, self)._validate()

        pbxhelper.pbxobj_validate_pbxobj_attr(self, u'pbx_buildConfigurationList', issues=issues)
        pbxhelper.pbxobj_validate_pbxobj_attr(self, u'pbx_mainGroup', issues=issues)
        pbxhelper.pbxobj_validate_pbxobj_attr(self, u'pbx_productRefGroup', issues=issues)

        pbxhelper.pbxobj_validate_pbxlist_attr(self, u'pbx_targets', self.is_valid_target, \
            resolved=resolved, issues=issues)

        dic = self.pbx_attributes.get(u'TargetAttributes')
        if not dic is None:
            if not func.isdict(dic):
                issues.append(u'invalid attributes.TargetAttributes: {0}'.format(dic))
            else:
                for k, v in dic.items():
                    if not self.hastarget(k):
                        dic.pop(k, None)
                        resolved.append(\
                            u'remove attribute for dangling target:{guid}'.format(guid=k))

        self.__validate_project_references(resolved, issues)
        self.__deduplicate_project_reference(resolved, issues)
        return resolved, issues

