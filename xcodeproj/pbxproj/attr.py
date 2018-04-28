#!/usr/bin/python
# encoding:utf-8
# 
# copyright (c) Alex Lee, All rights reserved.

import os
import sys
ModuleRoot = os.path.abspath(os.path.join(__file__, '../../..'))
if os.path.isdir(ModuleRoot) and not ModuleRoot in sys.path:
    sys.path.append(ModuleRoot)


class Attribute(object):

    def __init__(self, name, type=None, **kwargs):
        super(Attribute, self).__init__()
        self.__name = name
        self.__type = type

        if u'default' in kwargs:
            self.__default = kwargs[u'default']

    def __getattribute__(self, name):
        if name == u'name':
            return self.__name
        elif name == u'type':
            return self.__type
        # elif name in self.__kwargs:
        #     return self.__kwargs[name]
        return super(Attribute, self).__getattribute__(name)

    def getdefault(self):
        return self.__default

        # try:
        #     return super(type(obj), obj).__getattribute__(self.__name)
        # except AttributeError as e:
        #     return self.__default
        
    
    # def setvalue(self, obj, value):
    #     if self.__type is None or isinstance(value, self.__type):
    #         super(type(obj), obj).__setattr__(self.__name, value)
    #     else:
    #         raise ValueError(u'"{obj}.{attr}" expected "{t}" but not "{bad}".'\
    #             .format(obj=type(obj), attr=self.__name, t=self.__type, bad=type(value)))

__OBJ_ATTRS = dict()

def reg_attr(objtype, attr):
    clsname = objtype.__name__
    if clsname in __OBJ_ATTRS:
        __OBJ_ATTRS[clsname][attr.name] = attr
    else:
        __OBJ_ATTRS[clsname] = {attr.name: attr}

def has_reg_attr(obj, attr):
    for clstype in type(obj).__mro__:
        dic = __OBJ_ATTRS.get(clstype.__name__, None)
        if not dic is None:
            return attr in dic
    return False

def getvalue(obj, attr):
    try:
        for clstype in type(obj).__mro__:
            dic = __OBJ_ATTRS.get(clstype.__name__, None)
            if not dic is None:
                if attr in dic:
                    return dic[attr].getdefault()
    except KeyError as e:
        raise AttributeError(u'\'{o}\' object has no attribute \'{a}\''.format(o=obj, a=attr))

# def setvalue(obj, attr, value):
#     for clstype in type(obj).__mro__:
#         dic = __OBJ_ATTRS.get(clstype.__name__, None)
#         if not dic is None:
#             if attr in dic:
#                 return dic[attr].setvalue(obj, vaule)
#             else:
#                 return super(type(obj), obj).__setattr__(attr, value)
#     return super(type(obj), obj).__setattr__(attr, value)







