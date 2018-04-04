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

class PBXAbstract(object):

    def __getattribute__(self, name):
        if func.hasprefix(name, pbxconsts.PBX_ATTR_PREFIX):
            try:
                return super(PBXAbstract, self).__getattribute__(name)
            except Exception as e:
                return None
        else:
            return super(PBXAbstract, self).__getattribute__(name)

    def parse(self, objdict):
        """
        parse object attribute values from 'objdict'
        """
        for key in objdict.keys():
            value = objdict.pop(key)
            pbxkey = u'pbx_{name}'.format(name=key)
            
            if func.isseq(value):
                newarr = self.__parse_arr_attr_val(value)
                setattr(self, pbxkey, newarr)
            elif func.isdict(value):
                self.__parse_dict_attr_val(value)
                setattr(self, pbxkey, value)
            else:
                self.__parse_str_attr(pbxkey, value)
                
    def __parse_str_attr(self, pbxkey, value):
        if pbxhelper.is_valid_guid(value):
            obj = self._xcproj.get_object(value)
            if not obj is None:
                setattr(self, pbxkey, obj)
                obj.add_referrer(self)
                return 
        setattr(self, pbxkey, value)

    def __parse_arr_attr_val(self, arr):
        newarr = []
        for val in arr:
            if func.isstr(val) and pbxhelper.is_valid_guid(val):
                obj = self._xcproj.get_object(val)
                if not obj is None:
                    obj.add_referrer(self)
                    newarr.append(obj)
                else:
                    newarr.append(val) # error?
            elif func.isseq(val):
                newarr.append(self.__parse_arr_attr_val(val))
            elif func.isdict(val):
                self.__parse_dict_attr_val(val)
                newarr.append(val)
            else:
                newarr.append(val)
        return newarr

    def __parse_dict_attr_val(self, dic):
        for k, v in dic.items():
            if func.isstr(v) and pbxhelper.is_valid_guid(v):
                obj = self._xcproj.get_object(v)
                if not obj is None:
                    obj.add_referrer(self)
                    dic[k] = obj
            elif func.isseq(v):
                dic[k] = self.__parse_arr_attr_val(v)
            elif func.isdict(v):
                self.__parse_dict_attr_val(v)

    def pbxdict(self):
        """ return dict with pbx-attr and values (exclude guid) """
        dic = {k[len(pbxconsts.PBX_ATTR_PREFIX):]:v for k, v in self.__dict__.items() if func.hasprefix(k, pbxconsts.PBX_ATTR_PREFIX)}
        return dic

    def write(self, buff, identstr=u''):
        """
        format object to str in xcode pbxproj format
        :param  buff    list, the buff to write to
        """
        buff.append(identstr)
        buff.append(self._pbxstr_escape(self.guid))

        comment = self.comment()
        if not comment is None:
            buff.append(u' /* {comment} */'.format(comment=comment))

        buff.append(u' = ')
        pairs = sorted(self.pbxdict().items(), key=lambda e: 0 if e[0] == 'isa' else e[0])
        self._print_pairs(buff, pairs, identstr, singleline=self._print_in_one_line())
        buff.append(u';')

    def _print_pairs(self, buff, pairs, identstr, singleline=False):
        buff.append(u'{')
        if not singleline:
            buff.append(os.linesep)

        for k, v in pairs:
            self._print_kv(buff, k, v, identstr + u'\t', singleline)

        if not singleline:
            buff.append(identstr)
        buff.append(u'}')

    def _print_value(self, buff, val, identstr, singleline=False):
        from xcodeproj.pbxproj import baseobject
        # buff.append(u'')
        
        if func.isdict(val):
            pairs = sorted(val.items(), key=lambda e: e)
            self._print_pairs(buff, pairs, identstr, singleline)
        elif func.isseq(val):
            self._print_list(buff, val, identstr, singleline)
        elif isinstance(val, baseobject.PBXBaseObject):
            buff.append(self._pbxstr_escape(val.guid))
            comment = val.comment()
            if not comment is None:
                buff.append(u' /* {comment} */'.format(comment=comment))
        else:
            buff.append(self._pbxstr_escape(val))

    def _print_list(self, buff, obj, identstr, singleline=False):
        buff.append(u'(')
        if not singleline:
            buff.append(os.linesep)

        for o in obj:
            if not o is None:
                if not singleline:
                    buff.append(identstr + u'\t')
                self._print_value(buff, o, identstr+u'\t', singleline)
                buff.append(u',{sep}'.format(sep=u' ' if singleline else os.linesep))

        if not singleline:
            buff.append(identstr)
        buff.append(u')')

    def _print_kv(self, buff, key, val, identstr, singleline=False):
        if not key is None and not val is None:
            buff.append(u'' if singleline else identstr)
            buff.append(u'{key} = '.format(key=self._pbxstr_escape(key)))

            self._print_value(buff, val, identstr, singleline)
            buff.append(u';{sep}'.format(sep=u' ' if singleline else os.linesep))
        # else:
        #     raise ValueError(u'invalid value. {k} = {v}'.format(k=key, v=val))

    def _pbxstr_escape(self, val):
        replacements = [
                        (u'\\', u'\\\\'),
                        (u'\n', u'\\n'),
                        (u'"',  u'\\"'),
                        (u'\0', u'\\0'),
                        (u'\t', u'\\\t'),
                        (u'\'', u'\\\''),
                        ]
        import re
        if len(val) == 0 or not re.match('[a-zA-Z0-9\\._/]*', val).group(0) == val:
            for k, v in replacements:
                val = val.replace(k, v)
            return u'"{0}"'.format(val)
        return val

    def _print_in_one_line(self):
        return False