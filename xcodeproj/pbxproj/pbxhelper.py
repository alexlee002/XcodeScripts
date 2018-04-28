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
from xcodeproj.pbxproj import pbxconsts

def is_valid_guid(obj):
    """ return True if 'obj' is valid pbxobject refid """
    import re
    return re.match('^[\dA-F]{{{0}}}$'.format(pbxconsts.REFID_LEN), str(obj))

def pbxstr_escape(val):
    replacements = [
                    (u'\\', u'\\\\'),
                    (u'\n', u'\\n'),
                    (u'"',  u'\\"'),
                    (u'\0', u'\\0'),
                    (u'\t', u'\\\t'),
                    (u'\'', u'\\\''),
                    ]
    import re
    val = func.to_unicode(val)
    if len(val) == 0 or not re.match('[a-zA-Z0-9\\._/]*', val).group(0) == val:
        for k, v in replacements:
            val = val.replace(k, v)
        return u'"{0}"'.format(val)
    return val

def pbxobj_set_pbxobj_attr(obj, objclass, attr, value, validator):
    """
    set value for attribute 'name'. the value is instance of PBXBaseObject
    """
    oldval = getattr(obj, attr, None)
    if not oldval is None:
        oldval.remove_referrer(obj)

    if validator(value):
        super(objclass, obj).__setattr__(attr, value)
        value.add_referrer(obj, attr)
    elif value is None:
        delattr(obj, attr)
    else:
        logger.warn(u'{obj} illegal {attr}:{val}'\
            .format(obj=obj, attr=attr[len(pbxconsts.PBX_ATTR_PREFIX):], val=value))


def pbxobj_validate_pbxobj_attr(obj, attr, throw_exception=False, issues=[]):
    """
    validate the dependent object, 
    """
    from xcodeproj.pbxproj import baseobject
    depobj = getattr(obj, attr, None)
    if depobj is None:
        msg = u'{attr} is None'.format(attr=attr[len(pbxconsts.PBX_ATTR_PREFIX):])
        if throw_exception:
            raise baseobject.PBXValidationError(msg)
        else:
            issues.append(msg)
    try:
        depobj.validate()
    except baseobject.PBXValidationError as e:
        if throw_exception:
            raise # throw through
        else:
            issues.append(u'invalid {attr}: {ex}'\
                .format(attr=attr[len(pbxconsts.PBX_ATTR_PREFIX):], ex=e))


def pbxobj_set_pbxlist_attr(obj, objclass, attr, value, validator):
    """
    obj.attr is type of [PBXBaseObject] 
    """
    assert value is None or func.isseq(value)
    value = value if not value is None else []

    oldvalue = getattr(obj, attr, None)
    if not oldvalue is None:
        for oldv in oldvalue:
            oldv.remove_referrer(obj)

    if not value is None:
        rejects = []
        if func.isseq(value):
            value, rejects = func.filter_items(validator, value)
        else:
            value, rejects = ([], value)
        if len(rejects) > 0:
            logger.warn(u'{obj} ignore invalid {attr}:\n\t{v}'\
                .format(obj=obj, attr=attr[len(pbxconsts.PBX_ATTR_PREFIX):], \
                    v='\n\t'.join([str(v) for v in rejects])))

        super(objclass, obj).__setattr__(attr, value)
        for v in value:
            v.add_referrer(obj, attr)


def pbxobj_validate_pbxlist_attr(obj, attr, validator, resolved=[], issues=[]):
    from xcodeproj.pbxproj import baseobject
    vallist = getattr(obj, attr, [])
    index = 0
    while index < len(vallist):
        item = vallist[index]
        if item is None:
            vallist.pop(index)
        else:
            try:
                item.validate()
            except baseobject.PBXValidationError as e:
                pbxobj_remove_pbxlist_value(obj, attr, item, validator)
                resolved.append(u'remove invalid {0} {1}: {2}'\
                    .format(attr[len(pbxconsts.PBX_ATTR_PREFIX):], obj, e))
            else:
                index += 1

def pbxobj_has_pbxlist_value(obj, attr, value, validator):
    """
    return True if attribute 'name' of pbxobject 'obj' contains 'val'
    :param  obj:  object to check
    :param  attr:  pbxattribute name
    :param  value: value(pbxobject or guid) to check
    :param  validator: check if item is valid
    """
    guid = None
    if is_valid_guid(value):
        guid = value
    elif validator(value):
        guid = value.guid
    return not guid is None and len(func.take(lambda o: o.guid == guid, getattr(obj, attr, []))) > 0

def pbxobj_pbxlist_value_index(obj, attr, value, validator):
    """
    return index of value, -1 if not found
    """
    guid = None
    if is_valid_guid(value):
        guid = value
    elif validator(value):
        guid = value.guid

    if guid is None:
        return -1

    for index, val in enumerate(getattr(obj, attr, [])):
        if val.guid == guid:
            return index
    return -1


def pbxobj_add_pbxlist_value(obj, attr, val, validator, index=None):
    """"
    add value 'val' to attribute 'name' of  pbxobject 'obj'.
    the attribute value is list of pbxobjects
    :param  obj     pbxobject
    :param  name    pbxattribute name
    :param  val     value(pbxobject or guid) to remove
    :param  validator check if item is valid
    :param  index   the index of val to add
    """
    if pbxobj_has_pbxlist_value(obj, attr, val, validator):
        return

    if not validator(val):
        raise ValueError(\
            u'{obj} invalid {attr}: {v}'\
            .format(obj=obj, attr=attr[len(pbxconsts.PBX_ATTR_PREFIX):], v=val))

    if index is None:
        getattr(obj, attr).append(val)
    else:
        getattr(obj, attr).insert(index, val)
    val.add_referrer(obj, attr)

def pbxobj_remove_pbxlist_value(obj, attr, val, validator):
    """
    remove 'val' from attribute 'name' of pbxobject 'obj'
    :param  obj     pbxobject
    :param  name    pbxattribute name
    :param  val     value(pbxobject or guid) to remove
    :param  validator check if item is valid
    """
    guid = None
    if is_valid_guid(val):
        guid = val
    elif validator(val):
        guid = val.guid

    if not guid is None:
        attrval = getattr(obj, attr, [])
        index = 0
        while index < len(attrval):
            o = attrval[index]
            if guid == o.guid:
                attrval.pop(index)
                o.remove_referrer(obj)
                break
            index += 1

def pbxobj_replace_pbxlist_value(obj, attr, oldval, newval, validator):   
    if not validator(val):
        raise ValueError(\
            u'{obj} invalid {attr}: {v}'\
            .format(obj=obj, attr=attr[len(pbxconsts.PBX_ATTR_PREFIX):], v=newval))

    if not guid is None:
        attrval = getattr(obj, attr, [])
        for index, o in enumerate(attrval):
            if oldval.guid == o.guid:
                attrval[index] = newval
                o.remove_referrer(obj)
                newval.add_referrer(obj, attr)
                break

def pbxobj_replace_pbxobj_attr(obj, objclass, attr, oldval, newval, validator):
    """
    check if 'oldval' is the value of 'attr', 
    if True, replace it with 'newval', otherwise, do nothing
    """
    attrval = getattr(obj, attr, None)
    if not attrval is None and attrval.guid == oldval.guid:
        pbxobj_set_pbxobj_attr(obj, objclass, attr, newval, validator)

def pbxobj_deduplicate_pbxlist_value(obj, attr, key, action, resolved, issues):
    items = getattr(obj, attr, None)
    if items is None or len(items) < 2:
        return

    import itertools
    items = sorted(items, key=key)
    items = itertools.groupby(items, key=key)

    for k, lst in items:
        lst = list(lst)
        reserved = lst.pop(0)
        if len(lst) > 0:
            for delitem in lst:
                action(reserved, delitem)
            resolved.append(u'merge duplicate {attr} values to {r}:\n\t{dels}'\
                .format(attr=attr[len(pbxconsts.PBX_ATTR_PREFIX):],\
                    r=str(reserved), dels=u'\n\t'.join([str(o) for o in lst])))

def get_file_info(file):
    """
    return a tuple of the file's mimetype and charset
    """
    import re
    import subprocess

    p = subprocess.Popen(['/usr/bin/file', '-I', file], stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        matchs = re.search('.*:\s*(.+);.*\s*charset=(.+)', stdout)
        if matchs:
            mime = matchs.group(1)
            charset = matchs.group(2)
            return (mime, charset)
    return (None, None)

def osx_charset_num(charset):
    """
    convert the charset type to OSX's stringEncoding enum value
    """
    if charset == u'us-ascii':
        return 1 # NSASCIIStringEncoding
    elif charset == u'utf-8':
        return 4 # NSUTF8StringEncoding
    raise TypeError(u'unsupport charset: %s' % charset)
    #TODO: will be complete
    return None

def get_filetype(filepath):
    """ return file type for file with 'filepath' """
    ext = os.path.splitext(filepath)[1]
    if len(ext) > 0 and ext in pbxconsts.FILETYPE_BY_EXT:
        return pbxconsts.FILETYPE_BY_EXT[ext]
    
    mimetype, charset = get_file_info(filepath)
    if not mimetype is None and mimetype in pbxconsts.MIME_TO_FILETYPE:
        return pbxconsts.MIME_TO_FILETYPE[mimetype]
    else:
        logger.warn(u'not found PBXFileType for mimetype: {m}, path:{p}'\
            .format(m=mimetype, p=filepath))
        return u'file'

def buildphase_for_filetype(filetype):
    """ return buildphase isa that the file should be addws """
    if filetype in ['sourcecode.c.h', 'sourcecode.c.c.preprocessed']:
        return 'PBXHeadersBuildPhase'
    elif filetype in ['sourcecode.c.c', 'sourcecode.c.objc', 'sourcecode.cpp.cpp', \
        'sourcecode.cpp.objcpp']:
        return 'PBXSourcesBuildPhase'
    elif filetype in ['archive.ar', 'compiled.mach-o.dylib', \
        'sourcecode.text-based-dylib-definition', 'wrapper.framework']:
        return 'PBXFrameworksBuildPhase'
    else:
        return 'PBXResourcesBuildPhase'