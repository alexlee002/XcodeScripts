#!/usr/bin/python
# encoding:utf-8
# 
# copyright (c) Alex Lee, All rights reserved.

class PBXValidationError(Exception):
    pass

import os
import sys
ModuleRoot = os.path.abspath(os.path.join(__file__, '../../..'))
if os.path.isdir(ModuleRoot) and not ModuleRoot in sys.path:
    sys.path.append(ModuleRoot)

from xcodeproj.utils import func
from xcodeproj.utils import logger
from xcodeproj.pbxproj import pbxhelper
from xcodeproj.pbxproj import abstract
from xcodeproj.pbxproj import pbxconsts


class PBXBaseObject(abstract.PBXAbstract):
    
    def __init__(self, xcproj, guid):
        super(PBXBaseObject, self).__init__()
        self.guid = func.to_unicode(guid)
        self.__xcproj = xcproj

        self.__referrers = {} # {guid: referrer}
        self.__owners = None # {guid: owner}
        self.__dirty = True
        self.__dependencies = {} # {guid:set(keypath)}

    def __getattribute__(self, name):
        if name == u'isa':
            return self.__class__.__name__
        else:
            return super(PBXBaseObject, self).__getattribute__(name)

    def __setattr__(self, name, value):
        value = self.canonical_arg(value)
        if func.hasprefix(name, pbxconsts.PBX_ATTR_PREFIX):
            super(PBXBaseObject, self).__setattr__(name, value)
            self.__dirty = True
        else:
            super(PBXBaseObject, self).__setattr__(name, value)

    def __str__(self):
        return self.__unicode__().encode('utf-8')

    def __repr__(self):
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        if not self.guid is None or not self.isa is None:
            name = getattr(self, u'displayname', None)
            if not name is None:
                return u'[{guid}:{isa} ({name})]'.format(guid=self.guid, isa=self.isa, name=name())
            else:
                return u'[{guid}:{isa}]'.format(guid=self.guid, isa=self.isa)
        return super(PBXBaseObject, self).__unicode__()

    def project(self):
        return self.__xcproj

    def __add_dependency_attr(self, obj, keypath):
        """ self is the referrer of 'obj' """
        assert isinstance(obj, PBXBaseObject)
        guid = obj.guid
        keypaths = self.__dependencies.get(guid)
        if keypaths is None:
            self.__dependencies[guid] = set([keypath])
        elif keypath in keypaths:
            return
        else:
            self.__dependencies[guid].add(keypath)

    def __remove_dependency_attr(self, obj):
        assert isinstance(obj, PBXBaseObject)
        guid = obj.guid
        keypaths = self.__dependencies.get(guid)
        
        if not keypaths is None:
            for kp in keypaths:
                self.__check_and_replace_reference_object(kp, obj, None)
        self.__dependencies.pop(guid, None)

    def __check_and_replace_reference_object(self, keypath, oldval, newval):
        """
        if self.{keypath} == oldval; then self.{keypath} = newval.
        """
        def __replace_array_item(array, keys, oldval, newval):
            if len(keys) > 0:
                for subval in array:
                    __recursively_check_and_replace(subval, list(keys), oldval, newval)
            else:
                idx = 0
                while idx < len(array):
                    subval = array[idx]
                    if isinstance(subval, PBXBaseObject) and subval.guid == oldval.guid:
                        if newval is None:
                            array.pop(idx)
                        else:
                            if len(func.take(lambda a:a.guid == newval.guid, array)) == 0:
                                array[idx] = newval
                                newval.add_referrer(self, keypath)
                        subval.remove_referrer(self)
                    idx += 1
        # end of __replace_array_item

        def __recursively_check_and_replace(obj, keys, oldval, newval):
            if isinstance(obj, PBXBaseObject):
                __recursively_check_and_replace(obj.__dict__, keys, oldval, newval)
            elif func.isseq(obj):
                __replace_array_item(obj, keys, oldval, newval)

            elif func.isdict(obj):
                k = keys.pop(0)
                v = obj.get(k)

                if isinstance(v, PBXBaseObject) and v.guid == oldval.guid:
                    if newval is None:
                        obj.pop(k, None)
                    else:
                        obj[k] = newval
                        newval.add_referrer(self, keypath)
                    v.remove_referrer(self)
                elif func.isdict(v):
                    assert len(keys) > 0
                    __recursively_check_and_replace(v, keys, oldval, newval)
                elif func.isseq(v):
                    __replace_array_item(v, keys, oldval, newval)
        # end of __recursively_check

        __recursively_check_and_replace(self, keypath.split(u'.'), oldval, newval)

    def replace(self, obj):
        """
        replace obj with self in project's object-tree
        """
        if self == obj:
            assert self.__xcproj == obj.__xcproj
            return

        assert isinstance(obj, PBXBaseObject) \
            and self.isa == obj.isa and self.__xcproj == obj.__xcproj

        for ref in obj.referrers().values():
            for kp in ref.__keypaths_for_object(obj):
                ref.__check_and_replace_reference_object(kp, obj, self)
        assert len(obj.referrers()) == 0

    def remove_from_project(self):
        """ remove 'self' from project's object-tree, and remove from all referrers """
        self.__xcproj.remove_object(self)

    def __keypaths_for_object(self, attrval):
        guid = None
        if isinstance(attrval, abstract.PBXAbstract):
            guid = attrval.guid
        elif pbxhelper.is_valid_guid(attrval):
            guid = attrval

        if not guid is None and guid in self.__dependencies:
            return list(self.__dependencies[guid])
        return []
                    
    def referrers(self):
        """ 
        return {guid: object}, that the value object referred to 'self'
        eg:
            PBXBuildFile.fileRef = PBXFileReference
            so,
            PBXFileReference.referrs contains PBXBuildFile
        """
        return self.__referrers if not self.__referrers is None else {}

    def add_referrer(self, obj, keypath):
        """
        mark up that 'obj' referred to self
        """
        refer = None
        if isinstance(obj, abstract.PBXAbstract):
            self.__xcproj.add_object(obj)
            refer = obj
        elif func.isstr(obj):
            refer = self.__xcproj.get_object(obj)
            if refer is None:
                raise ValueError(u'[XcodeProj] object not found:{0}'.format(obj))

        if not refer is None:
            self.__referrers[refer.guid] = refer
            refer.__add_dependency_attr(self, keypath)
            self.__owners = None # need to re-caculate owners

    def remove_referrer(self, obj):
        """
        mark up that 'obj' no longer referred to self
        """
        if isinstance(obj, abstract.PBXAbstract):
            self.__referrers.pop(obj.guid, None)
            obj.__remove_dependency_attr(self)
        elif func.isstr(obj):
            guid = unicode(obj)
            self.__referrers.pop(guid, None)
            obj = self.__xcproj.get_object(obj)
            if not obj is None:
                obj.__remove_dependency_attr(self)

        if len(self.__referrers) == 0:
            self.__xcproj.remove_object(self)
        self.__owners = None # need to re-caculate owners

    def comment(self):
        """ xcode pbxproj comment """
        return None

    def allow_multi_owners(self):
        """ if 'self' can have more than 1 parent object """
        return False

    def owners(self):
        """ return the parent objects """
        if self.__owners is None:
            self.__owners = {guid:ref \
                for guid, ref in self.referrers().items() if self._accepted_owner(ref)}
        return self.__owners

    def _accepted_owner(self, obj):
        """ return True if obj can be accepted as parent of self """
        return False

    def hasowner(self, owner):
        """ return True if 'owner' is the parent object of self """
        if isinstance(owner, PBXBaseObject):
            return owner.guid in self.owners()
        elif bpxhelper.is_valid_guid(owner):
            return owner in self.owners()
        return False

    def has_multi_owners(self):
        """ return True if self has more than 1 parent-objects """
        return len(self.owner()) > 1

    def duplicate(self, xcproj=None):
        """
        duplicate a new object by coping attributes from self.
        :param xcproj: if is not None, the new-duplicted object will add to xcproj
        """
        if xcproj is None:
            xcproj = self.__xcproj
        cpobj = xcproj.new_object(self.isa)
        for attr, val in self.__dict__.items():
            cpobj._duplicate_attr(attr, val)
        return cpobj

    def _duplicate_attr(self, attr, val):
        if func.hasprefix(attr, pbxconsts.PBX_ATTR_PREFIX):
            setattr(self, attr, val)

    def equalto(self, other):
        """
        return True if self is equality to other.
        why not use __eq__:
            "==" use to check if the two objects are point to the SAME MEMERY ADDRESS.
            "equalTo" use to check the equality
        """
        if isinstance(other, PBXBaseObject):
            return self.pbxdict() == other.pbxdict() 
        return False               

    def pbxdict(self):
        """ override """
        dic = super(PBXBaseObject, self).pbxdict()
        dic[u'isa'] = self.isa
        return dic

    def validate(self):
        """ validate the object """

        if self.isdirty():
            resolved, issues = self._validate()
            self.__dirty = False

            if len(resolved) > 0:
                logger.verbose(u'========= {obj} ========={sep}{msg}{sep}'\
                    .format(obj=self, msg=os.linesep.join(resolved), sep=os.linesep))

            if len(issues) > 0:
                logger.verbose(u'========= {obj} ========={sep}{msg}{sep}'\
                    .format(obj=self, msg=os.linesep.join(issues), sep=os.linesep))

    def _validate(self):
        resolved = []
        issues = []

        if not pbxhelper.is_valid_guid(self.guid):
            issues.append(u'illegal guid:{guid}.'.format(self.guid))
        if not self.__xcproj.get_object(self.guid) == self:
            issues.append(u'{o} not in project\'s object tree!!!'.format(o=self))
        return resolved, issues

    def markdirty(self):
        """ mark up that the object has changed and need validate """
        self.__dirty = True

    def isdirty(self):
        """ return True if the object has changed since last validation """
        return self.__dirty


