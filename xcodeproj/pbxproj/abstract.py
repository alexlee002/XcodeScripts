#!/usr/bin/python
# encoding:utf-8
# 
# copyright (c) Alex Lee, All rights reserved.

import os
import sys
ModuleRoot = os.path.abspath(os.path.join(__file__, '../../..'))
if os.path.isdir(ModuleRoot) and not ModuleRoot in sys.path:
    sys.path.append(ModuleRoot)

from xcodeproj.utils import func
from xcodeproj.utils import logger
from xcodeproj.pbxproj import pbxhelper
from xcodeproj.pbxproj import pbxconsts
from xcodeproj.pbxproj import attr

class PBXAbstract(object):

    def __getattribute__(self, name):
        if func.hasprefix(name, pbxconsts.PBX_ATTR_PREFIX):
            try:
                return super(PBXAbstract, self).__getattribute__(name)
            except AttributeError as e:
                return None #attr.getvalue(self, name)
        else:
            return super(PBXAbstract, self).__getattribute__(name)

    def canonical_arg(self, arg):
        def __dispatch(obj):
            if func.isseq(obj):
                return __canonical_list(list(obj))
            elif func.isdict(obj):
                return __canonical_dict(obj)
            else:
                return __canonical_obj(obj)

        def __canonical_obj(obj):
            return obj.decode('utf-8') if isinstance(obj, str) else obj

        def __canonical_list(lst):
            newlst = []
            for obj in lst:
                newlst.append(__dispatch(obj))
            return newlst

        def __canonical_dict(dic):
            pairs = []
            for k, v in dic.items():
                pairs.append((__canonical_obj(k), __dispatch(v)))
            return dict(pairs)
        # end of sub-funcs

        return __dispatch(arg)

    def parse(self, objdict):
        """
        parse object attribute values from 'objdict'
        """
        objdict.pop(u'isa', None)
        for key in objdict.keys():
            value = objdict.pop(key)
            pbxkey = u'pbx_{name}'.format(name=key)
            
            if func.isseq(value):
                newarr = self.__parse_arr_attr_val(value, pbxkey)
                setattr(self, pbxkey, newarr)
            elif func.isdict(value):
                self.__parse_dict_attr_val(value, pbxkey)
                setattr(self, pbxkey, value)
            else:
                self.__parse_str_attr(pbxkey, value)
                
    def __parse_str_attr(self, pbxkey, value):
        if pbxhelper.is_valid_guid(value):
            obj = self.project().get_object(value)
            if not obj is None:
                setattr(self, pbxkey, obj)
                obj.add_referrer(self, pbxkey)
                return
        setattr(self, pbxkey, value)

    def __parse_arr_attr_val(self, arr, pbxkey):
        newarr = []
        for val in arr:
            if func.isstr(val) and pbxhelper.is_valid_guid(val):
                obj = self.project().get_object(val)
                if not obj is None:
                    obj.add_referrer(self, pbxkey)
                    newarr.append(obj)
                else:
                    newarr.append(val) # error?
            elif func.isseq(val):
                newarr.append(self.__parse_arr_attr_val(val, pbxkey))
            elif func.isdict(val):
                self.__parse_dict_attr_val(val, pbxkey)
                newarr.append(val)
            else:
                newarr.append(val)
        return newarr

    def __parse_dict_attr_val(self, dic, pbxkey):
        for k, v in dic.items():
            depkey = u'{0}.{1}'.format(pbxkey, k)
            if func.isstr(v) and pbxhelper.is_valid_guid(v):
                obj = self.project().get_object(v)
                if not obj is None:
                    obj.add_referrer(self, depkey)
                    dic[k] = obj
                else:
                    dic[k] = v
            elif func.isseq(v):
                dic[k] = self.__parse_arr_attr_val(v, depkey)
            elif func.isdict(v):
                self.__parse_dict_attr_val(v, depkey)

    def pbxdict(self):
        """ return dict with pbx-attr and values (exclude guid) """
        dic = {k[len(pbxconsts.PBX_ATTR_PREFIX):]:v \
            for k, v in self.__dict__.items() if func.hasprefix(k, pbxconsts.PBX_ATTR_PREFIX)}
        return dic

    def safely_write(self, buff, val):
        buff.append(func.to_unicode(val))

    def write(self, buff, identstr=u''):
        """
        format object to str in xcode pbxproj format
        :param  buff    list, the buff to write to
        """
        self.safely_write(buff, identstr)
        self.safely_write(buff, pbxhelper.pbxstr_escape(self.guid))

        comment = self.comment()
        if not comment is None:
            self.safely_write(buff, u' /* {cmt} */'.format(cmt=comment))

        self.safely_write(buff, u' = ')
        pairs = sorted(self.pbxdict().items(), key=lambda e: 0 if e[0] == u'isa' else e[0])
        self._print_pairs(buff, pairs, identstr, singleline=self._print_in_one_line())
        self.safely_write(buff, u';')

    def _print_pairs(self, buff, pairs, identstr, singleline=False):
        self.safely_write(buff, u'{')
        if not singleline:
            self.safely_write(buff, u'{sep}'.format(sep=os.linesep))

        for k, v in pairs:
            self._print_kv(buff, k, v, identstr + u'\t', singleline)

        if not singleline:
            self.safely_write(buff, identstr)
        self.safely_write(buff, u'}')

    def _print_value(self, buff, val, identstr, singleline=False):
        from xcodeproj.pbxproj import baseobject
        # self.safely_write(buff, u'')
        
        if func.isdict(val):
            pairs = sorted(val.items(), key=lambda e: e)
            self._print_pairs(buff, pairs, identstr, singleline)
        elif func.isseq(val):
            self._print_list(buff, val, identstr, singleline)
        elif isinstance(val, baseobject.PBXBaseObject):
            self.safely_write(buff, pbxhelper.pbxstr_escape(val.guid))
            comment = val.comment()
            if not comment is None:
                self.safely_write(buff, u' /* {comment} */'.format(comment=comment))
        else:
            self.safely_write(buff, pbxhelper.pbxstr_escape(val))

    def _print_list(self, buff, obj, identstr, singleline=False):
        self.safely_write(buff, u'(')
        if not singleline:
            self.safely_write(buff, u'{sep}'.format(sep=os.linesep))

        for o in obj:
            if not o is None:
                if not singleline:
                    self.safely_write(buff, identstr + u'\t')
                self._print_value(buff, o, identstr+u'\t', singleline)
                self.safely_write(buff, u',{sep}'.format(sep=u' ' if singleline else os.linesep))

        if not singleline:
            self.safely_write(buff, identstr)
        self.safely_write(buff, u')')

    def _print_kv(self, buff, key, val, identstr, singleline=False):
        if not key is None and not val is None:
            self.safely_write(buff, u'' if singleline else identstr)
            self.safely_write(buff, u'{key} = '.format(key=pbxhelper.pbxstr_escape(key)))

            self._print_value(buff, val, identstr, singleline)
            self.safely_write(buff, u';{sep}'.format(sep=u' ' if singleline else os.linesep))
        # else:
        #     raise ValueError(u'invalid value. {k} = {v}'.format(k=key, v=val))

    

    def _print_in_one_line(self):
        return False