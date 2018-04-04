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
        projectReferences       dict, nullable
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
            pbxhelper.set_pbxobj_value(self, PBXProject, name, value, \
                lambda o:isinstance(o, baseobject.PBXBaseObject) and o.isa == 'XCConfigurationList')

        elif name in [u'pbx_mainGroup', u'pbx_productRefGroup']:
            pbxhelper.set_pbxobj_value(self, PBXProject, name, value, \
                lambda o:isinstance(o, baseobject.PBXBaseObject) and o.isa == 'PBXGroup')

        elif name == u'pbx_targets':
            pbxhelper.set_pbxobj_list_value(self, PBXProject, name, value, self.is_valid_target)

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

        value, rejects = func.filter_items(\
            lambda o: func.isdict(o) \
            and o[u'ProductGroup'].isa == u'PBXGroup' \
            and o[u'ProjectRef'].isa == u'PBXFileReference', value)
        if len(rejects) > 0:
            logger.warn(u'{0} ignore invalid project reference:\n\t{1}'\
                .format(self, u'\n\t'.join(map(lambda o: str(o), rejects))))

        super(PBXProject, self).__setattr__(u'pbx_projectReferences', value)

    def is_valid_target(self, obj):
        from xcodeproj.pbxproj.objects import target
        return isinstance(obj, target.PBXTarget)

    def hastarget(self, target):
        """
        return True if contains target 
        :param  target   guid or target object
        """
        return pbxhelper.pbxobj_has_list_value(self, u'pbx_targets', target, \
            self.is_valid_target)

    def addtarget(self, target, index=None):
        """ add target to this project """
        pbxhelper.pbxobj_add_list_value(self, u'pbx_targets', target, self.is_valid_target, \
            index=index)

    def removetarget(self, target):
        """ 
        remove target 
        :param target    target object or guid to be removed
        """
        pbxhelper.pbxobj_remove_list_value(self, u'pbx_targets', target, self.is_valid_target)

    def abspath(self):
        return self._xcproj.project_dir()

    def displayname(self):
        return self._xcproj.project_name()

    def comment(self):
        """ override """
        return u'Project object'

    def _validate(self):
        resolved, issues = super(PBXProject, self)._validate()

        pbxhelper.validate_dependent_object(self, u'pbx_buildConfigurationList', issues=issues)
        pbxhelper.validate_dependent_object(self, u'pbx_mainGroup', issues=issues)
        pbxhelper.validate_dependent_object(self, u'pbx_productRefGroup', issues=issues)

        for obj in self.pbx_targets:
            try:
                obj.validate()
            except Exception as e:
                if isinstance(e, baseobject.PBXValidationError):
                    self.removetarget(obj)
                    resolved.append(u'remove invalid child {0}; reason: {1}'.format(obj, e))
                else:
                    raise

        dic = func.get_dict_val(self.pbx_attributes, 'TargetAttributes')
        if not dic is None:
            if not func.isdict(dic):
                issues.append(u'invalid attributes.TargetAttributes: {0}'.format(dic))
            else:
                for k, v in dic.items():
                    if not self.hastarget(k):
                        dic.pop(k, None)
                        resolved.append(\
                            u'remove attribute for dangling target:{guid}'.format(guid=k))

        prodrefs = self.pbx_projectReferences
        if not prodrefs is None:
            if not func.isseq(prodrefs):
                issues.append(u'illegal projectReferences: {ref}'.format(ref=prodrefs))
            else:
                for refdict in list(prodrefs):
                    if not func.isdict(refdict):
                        prodrefs.remove(refdict)
                        issues.append(u'invalid projectReference:{ref}'.format(ref=refdict))
                    else:
                        refgroup = func.get_dict_val(refdict, u'ProductGroup')
                        if refgroup is None:
                            prodrefs.remove(refdict)
                            issues.append(u'invalid ProductGroup:{ref}'.format(ref=refgroup))
                        else:
                            try:
                                refgroup.validate()
                            except Exception as e:
                                if isinstance(e, baseobject.PBXValidationError):
                                    prodrefs.remove(refdict)
                                    resolved.append(u'invalid ProductGroup:{pg}; {ex}'\
                                        .format(pg=refgroup, ex=e))

        return resolved, issues

