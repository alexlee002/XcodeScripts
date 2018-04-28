#!/usr/bin/python
# encoding:utf-8
# 
# copyright (c) Alex Lee, All rights reserved.

import os
import sys
ModuleRoot = os.path.abspath(os.path.join(__file__, '../../../..'))
if os.path.isdir(ModuleRoot) and not ModuleRoot in sys.path:
    sys.path.append(ModuleRoot)

import itertools

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
            pbxhelper.pbxobj_set_pbxlist_attr(self, PBXGroup, name, value, self.is_valid_child)
        elif name == u'pbx_path':
            pbxpath.set_group_file_path(self, PBXGroup, value)
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

    def allow_children_types(self):
        """ allowed child types """
        return [u'PBXFileReference', u'PBXGroup', u'PBXReferenceProxy', u'PBXVariantGroup']

    def is_valid_child(self, child):
        """ return True if child is valid """
        return isinstance(child, baseobject.PBXBaseObject) \
            and child.isa in self.allow_children_types()

    def addfile(self, abspath, sourcetree=pbxconsts.SOURCE_TREE.group, move=True):
        """ add file reference at abspath to this group """
        fileref = self.project().fileref_for_path(abspath)
        if fileref is None:
            fileref = self.project().new_object(u'PBXFileReference')
            pbxpath.set_path_with_source_tree(fileref, abspath, source_tree=sourcetree, \
                parent_group=self)
            fileref.pbx_lastKnownFileType = pbxhelper.get_filetype(abspath)
        self.addchild(fileref, move=move)
        return fileref

    def addgroup(self, abspath=None, sourcetree=pbxconsts.SOURCE_TREE.group, name=None, move=True):
        """
        return the group object specified the 'abspath',  not include the children
        :param abspath:     the group's abspath in disk, if None, using the parent's path
        """
        group_name = os.path.basename(abspath) if name is None or len(name) == 0 else name
        abspath = abspath if not abspath is None else self.realpath()
        subgroup = func.get_list_item(func.take(\
            lambda o: o.isa == u'PBXGroup' and o.realpath() == abspath \
            and o.displayname() == group_name, self.pbx_children), 0)
        if subgroup is None:
            subgroup = self.project().new_object(u'PBXGroup')
            pbxpath.set_path_with_source_tree(subgroup, abspath, source_tree=sourcetree, \
                parent_group=self)
            if not name is None:
                subgroup.pbx_name = name
        self.addchild(subgroup, move=move)
        return subgroup

    def add_variant_group(self, rootpath, filename, sourcetree=pbxconsts.SOURCE_TREE.group, \
        move=True):
        """
        return the variant group specified the file 'filename', not include the children
        :param rootpath: the directory to 'xxx.lproj', eg: rootpath/en.lproj
        :param filename: the locaized file, eg rootpath/en.lproj/filename
        """
        vgroup = xcproj.get_variant_group(rootpath, filename)
        if vgroup is None:
            vgroup = xcproj.new_object(u'PBXVariantGroup')
            pbxpath.set_path_with_source_tree(vgroup, rootpath, parent_group=self)
            vgroup.pbx_name = filename
        self.addchild(vgroup, move=move)
        return vgroup

    def haschild(self, child):
        """
        return True if contains child 
        :param  child   guid or child object
        """
        return pbxhelper.pbxobj_has_pbxlist_value(self, u'pbx_children', child, \
            self.is_valid_child)

    def can_add_child(self, child):
        """ 
        return true if 'child' can be add to self 
        """
        if not self.is_valid_child(child):
            return False
        if child.isa == u'PBXGroup':
            return len(func.take(\
                lambda c: c.pbx_name == child.pbx_name and c.realpath() == child.realpath(),\
                self.pbx_children)) == 0
        else:
            return len(func.take(lambda c:c.realpath() == child.realpath(), self.pbx_children)) == 0

    def addchild(self, child, index=None, move=True):
        """ 
        add child object to group 
        :param  child:  the object to add
        :param  index:  insert object to specified index
        :param  move:   True: if object already has another owner, move it to this group
        """
        owners = child.owners()
        if len(owners) > 0 and not move:
            return # keep the original owner

        if self.guid in owners:
            return # already add

        # add to this group (avoid 'child' being remove from project when no one refer to it)
        pbxhelper.pbxobj_add_pbxlist_value(self, u'pbx_children', child, \
            self.is_valid_child, index=index)

        for owner in owners.values():
            child.remove_referrer(owner) # remove from other groups

    def removechild(self, child):
        """
        remove child 
        :param  child   guid or child object
        """
        pbxhelper.pbxobj_remove_pbxlist_value(self, u'pbx_children', child, \
            self.is_valid_child)

    def displayname(self):
        """ the name of self to be displayed """
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
        return pbxpath.realpath(self.project(), self.abspath())

    # def get_children(self, selector, recursively=False):
    #     """
    #     return list of children, filter by function 'selector'
    #     :param selector:    function to filter objects
    #     :param recursively: if True, recursively search the sub-groups
    #     """
    #     def __recursively_search(parent, selector, result):
    #         groups, files = func.filter_items(lambda c: c.isa == u'PBXGroup', parent.pbx_children)
    #         files = [f for f in files if selector(f)]
    #         result.extend(files)
    #         if recursively:
    #             for g in groups:
    #                 __recursively_search(g, selector, result)
    #     # end of __recursively_search
    #     result = []
    #     __recursively_search(self, selector, result)
    #     return result

    def _validate_children(self, resolved, issues):
        pbxhelper.pbxobj_validate_pbxlist_attr(\
            self, u'pbx_children', self.is_valid_child, resolved=resolved, issues=issues)

        def __group_key(obj):
            if isinstance(obj, PBXGroup):
                return u'{isa}:{name}@{path}'.format(\
                    isa=obj.isa,
                    name=obj.pbx_name if not obj.pbx_name is None else u'',\
                    path=obj.realpath())
            else:
                return obj.realpath()

        def __deduplicate_action(reserved, delchild):
            if isinstance(delchild, PBXGroup):
                for subch in delchild.pbx_children:
                    reserved.addchild(subch)
                    delchild.removechild(subch)
            self.removechild(delchild)
            reserved.replace(delchild)

        pbxhelper.pbxobj_deduplicate_pbxlist_value(self, u'pbx_children', \
            __group_key, __deduplicate_action, resolved, issues)

    def _validate(self):
        resolved, issues = super(PBXGroup, self)._validate()
        self._validate_children(resolved, issues)

        if self.pbx_sourceTree is None:
            issues.append(u'{0} invalid sourceTree: {1}'.format(self, self.pbx_sourceTree))
        elif not self == self.project().pbx_rootObject.pbx_mainGroup \
            and not func.isstr(self.pbx_name) and not func.isstr(self.pbx_path):
            issues.append(u'{0} invalid name / path.'.format(self))
        return resolved, issues

    def comment(self):
        """ override """
        return self.displayname()


class PBXVariantGroup(PBXGroup):
    pass



