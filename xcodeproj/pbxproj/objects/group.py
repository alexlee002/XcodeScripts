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
from xcodeproj.pbxproj import pbxpath
from xcodeproj.utils import func

class PBXGroup(baseobject.PBXBaseObject):
    """
    owner: PBXProject / PBXGroup
    relative:    one[owner] to many

    pbx-attr:
        children        [@is_valid_child], nonnull, default []
        name            str, nullable
        sourceTree      str, nonnull, default '<group>'
        path            str, nullable
    """

    def __init__(self, xcproj, guid):
        super(PBXGroup, self).__init__(xcproj, guid)
        self.pbx_children = [] # [pbxobject]
        self.pbx_sourceTree = pbxconsts.SOURCE_TREE.group # str

        # self.__realpath = None # str, real path on disk
        self.__abspath = None # str, project relative path


    def __setattr__(self, name, value):
        if name == u'pbx_children':
            pbxhelper.set_pbxobj_list_value(self, PBXGroup, name, value, self.is_valid_child)
        else:
            super(PBXGroup, self).__setattr__(name, value)

    def _accepted_owner(self, obj):
        if not isinstance(obj, baseobject.PBXBaseObject):
            return False
        if obj.isa == u'PBXGroup' and obj.haschild(self):
            return True
        if obj.isa == u'PBXProject' and self == obj.pbx_mainGroup:
            return True
        return False

    def duplicate(self):
        """ override """
        obj = super(PBXGroup, self).duplicate()
        for attr, val in self.__dict__.items():
            if func.hasprefix(attr, pbxconsts.PBX_ATTR_PREFIX):
                setattr(obj, attr, val)
        return obj

    def allow_children_types(self):
        """ allowed child types """
        return [u'PBXFileReference', u'PBXGroup', u'PBXReferenceProxy', u'PBXVariantGroup']

    def is_valid_child(self, child):
        """ return True if child is valid """
        return isinstance(child, baseobject.PBXBaseObject) \
            and child.isa in self.allow_children_types()

    def haschild(self, child):
        """
        return True if contains child 
        :param  child   guid or child object
        """
        return pbxhelper.pbxobj_has_list_value(self, u'pbx_children', child, \
            self.is_valid_child)


    def addchild(self, child, index=None):
        """ add child object to group """
        pbxhelper.pbxobj_add_list_value(self, u'pbx_children', child, \
            self.is_valid_child, index=index)

        if child.pbx_sourceTree == pbxconsts.SOURCE_TREE_ENMU.group \
            and not child.realpath() == self.realpath():
            child.pbx_path = os.path.relpath(child.realpath(), self.realpath())

    def removechild(self, child):
        """
        remove child 
        :param  child   guid or child object
        """
        pbxhelper.pbxobj_remove_list_value(self, u'pbx_children', child, \
            self.is_valid_child)

    def displayname(self):
        if not self.pbx_name is None:
            return self.pbx_name
        if not self.pbx_path is None:
            return os.path.basename(self.pbx_path)
        return None

    def abspath(self):
        """ return path in project """
        if self.__abspath is None:
            self.__abspath = pbxpath.abspath(self)
        return self.__abspath

    def realpath(self):
        """ return path on disk """
        return pbxpath.realpath(self._xcproj, self.abspath())

    def _validate_child(self, resolved, issues):
        path_dict = dict()
        for obj in self.pbx_children:
            try:
                obj.validate()
            except Exception as e:
                if obj is None or isinstance(e, baseobject.PBXValidationError):
                    self.removechild(obj)
                    resolved.append(u'remove invalid child {0}; reason: {1}'.format(obj, e))
                    continue
                else:
                    raise
            # caculate duplicate childrens
            # how duplicate children made? for example: git merge, especilly when conflict occurs
            if obj.isa in [u'PBXFileReference', u'PBXReferenceProxy']:
                realpath = obj.realpath()
                if not realpath in path_dict:
                    path_dict[realpath] = [obj]
                else:
                    path_dict[realpath].append(obj)


        for path, objs in path_dict.items():
            if len(objs) > 1:
                removingobjs = objs if path is None else objs[1:]
                for obj in removingobjs:
                    self.removechild(obj)
                resolved.append(\
                    u'remove duplicate children of path "{path}":\n\t{objs}'\
                    .format(path=path, objs=u'\n\t'.join([str(o) for o in removingobjs])))

    def _validate(self):
        resolved, issues = super(PBXGroup, self)._validate()
        self._validate_child(resolved, issues)

        if self.pbx_sourceTree is None:
            issues.append(u'{0} invalid sourceTree: {1}'.format(self, self.pbx_sourceTree))
        elif not self == self._xcproj.pbx_rootObject.pbx_mainGroup \
            and not func.isstr(self.pbx_name) and not func.isstr(self.pbx_path):
            issues.append(u'{0} invalid name / path.'.format(self))
        return resolved, issues

    def comment(self):
        """ override """
        return self.displayname()


class PBXVariantGroup(PBXGroup):
    pass



