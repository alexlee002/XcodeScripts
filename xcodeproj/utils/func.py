#!/usr/bin/python
# encoding:utf-8
# 
# copyright (c) Alex Lee, All rights reserved.


def isdict(obj):
    """ return True if 'obj' is a dict """
    if isinstance(obj, dict):
        return True
    import collections
    return isinstance(obj, collections.OrderedDict)


def isseq(obj):
    """ return True if 'obj' is list/set/tuple """
    return isinstance(obj, list) or isinstance(obj, set) or isinstance(obj, tuple)


def isstr(obj):
    """ return True if 'obj' is str/unicode """
    return isinstance(obj, unicode) or isinstance(obj, str)


def get_dict_val(dic, key, dftval=None):
    """ return value for 'key' in 'dic', or None if no such key """
    return dic[key] if key in dic else dftval

def get_list_item(l, pos, dftval=None):
    """ return array item at index 'pos' """
    return l[pos] if pos < len(l) else dftval

def take(func, l, s=1):
    """ take first 's' items from sequence 'l' with filter 'func' """
    ret = []
    for item in l:
        if func(item) and len(ret) < s:
            ret.append(item)
    return ret

def filter_items(func, l):
    """ 
    seperate list 'l' into two list: 'selected' and 'rejected' by function 'func'
    """
    selects = []
    rejects = []
    for o in l:
        if func(o):
            selects.append(o)
        else:
            rejects.append(o)
    return selects, rejects


def hasprefix(string, prefix):
    """ test if string has prefix """
    return string[0:min(len(string), len(prefix))] == prefix


def hassubfix(string, subfix):
    """ test if string has subfix """
    if len(subfix) > len(string):
        return False
    return string[(len(string) - len(subfix)):] == subfix

def issubpath(parent, subpath):
    """ return True if 'subpath' is subpath of 'parent' """
    import os
    
    parent = os.path.normpath(parent)
    subpath = os.path.normpath(subpath)
    return hasprefix(subpath, parent + os.sep)


def callerinfo(framenum=1, shortfilename=True):
    """
    return the caller info: #func, #file, #line
    """

    import inspect
    import os
    stack = inspect.stack()
    if len(stack) < (framenum+1):
        return (None, None, None)

    caller = stack[framenum]
    assert len(caller) > 4
    return (caller[3], os.path.basename(caller[1]) if shortfilename else caller[1], caller[2])