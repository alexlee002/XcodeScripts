#!/usr/bin/python
# encoding:utf-8
# 
# copyright (c) Alex Lee, All rights reserved.

import os
import sys
ModuleRoot = os.path.abspath(os.path.join(__file__, '../../..'))
if os.path.isdir(ModuleRoot) and not ModuleRoot in sys.path:
    sys.path.append(ModuleRoot)

from xcodeproj.pbxproj import abstract
from xcodeproj.pbxproj import baseobject
from xcodeproj.pbxproj import pbxhelper
from xcodeproj.utils import func

class PBXObjects(abstract.PBXAbstract):

    def __init__(self):
        super(PBXObjects, self).__init__()
        self.__objects = dict()
        self.__sections = dict()

    def guids(self):
        return self.__objects.keys()

    def guid_items(self):
        return self.__objects.items()

    def sections(self):
        return self.__sections.keys()

    def section_items(self):
        return self.__sections.items()

    def __setitem__(self, key, value):
        assert isinstance(value, baseobject.PBXBaseObject)

        isa = getattr(value, u'isa')
        assert not isa is None
        if isa in self.__sections:
            self.__sections[isa][key] = value
        else:
            self.__sections[isa] = {key: value}
        self.__objects[key] = value
        assert self.__validate()

    def __getitem__(self, key):
        if pbxhelper.is_valid_guid(key):
            return func.get_dict_val(self.__objects, key)
        return func.get_dict_val(self.__sections, key)

    def __delitem__(self, key):
        if pbxhelper.is_valid_guid(key):
            self.__objects.pop(key, None)
            for sec in self.__sections.values():
                sec.pop(key, None)
        else:
            objs = self.__sections.pop(key, None)
            if objs is None:
                raise KeyError('No such key: {0}'.format(key))
            else:
                for obj in objs:
                    self.__objects.pop(obj.guid, None)
        assert self.__validate()

    def __contains__(self, key):
        if pbxhelper.is_valid_guid(key):
            return self.__objects.__contains__(key)
        return self.__sections.__contains__(key)

    def __validate(self):
        count = len(self.__objects)
        for objs in self.__sections.values():
            count -= len(objs)
            if count < 0:
                break
        return count == 0

    def write(self, buff, identstr=u''):
        """ override """
        for isa, objsdict in sorted(self.__sections.items(), key=lambda o: o[0]):
            buff.append(u'{sep}/* Begin {isa} section */{sep}'.format(isa=isa, sep=os.linesep))
            for guid, obj in sorted(objsdict.items(), key=lambda o:o[0]):
                obj.write(buff, identstr+u'\t')
                buff.append(os.linesep)
            buff.append(u'/* End {isa} section */{sep}'.format(isa=isa, sep=os.linesep))





        
