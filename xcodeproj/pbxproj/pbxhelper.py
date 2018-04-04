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

def set_pbxobj_value(obj, objtype, name, value, validator):
    """
    set pbxobject attribute value.
    the attribute value is instnace of pbxobject
    """
    oldval = getattr(obj, name, None)
    if not oldval is None:
        oldval.remove_referrer(obj)

    if validator(value):
        obj._xcproj.add_object(value)
        super(objtype, obj).__setattr__(name, value)
        value.add_referrer(obj)
    else:
        raise ValueError(u'{obj} illegal {attr}:{val}'\
            .format(obj=obj, attr=name[len(pbxconsts.PBX_ATTR_PREFIX):], val=value))

def set_pbxobj_list_value(obj, objtype, name, value, validator):
    """
    set value 'val' to attribute 'name' of  pbxobject 'obj'.
    the attribute value is list of pbxobjects
    """
    oldvalues = getattr(obj, name, None)
    if not oldvalues is None:
        for oldv in oldvalues:
            oldv.remove_referrer(obj)

    if func.isseq(value):
        value, rejects = func.filter_items(validator, value)
        if len(rejects) > 0:
            logger.warn(u'{obj} ignore invalid {attr}:\n\t{v}'\
                .format(obj=obj, attr=name[len(pbxconsts.PBX_ATTR_PREFIX):], v='\n\t'.join(rejects)))
    else:
        logger.warn(u'{obj} ignore invalid {attr}:{v}'\
            .format(obj, attr=name[len(pbxconsts.PBX_ATTR_PREFIX):], v=files))
        value = []
    for v in value:
        obj._xcproj.add_object(v)
        v.add_referrer(obj)
    super(objtype, obj).__setattr__(name, value)

def pbxobj_has_list_value(obj, name, val, validator):
    """
    return True if attribute 'name' of pbxobject 'obj' contains 'val'
    :param  obj   object to check
    :param  name  pbxattribute name
    :param  value value(pbxobject or guid) to check
    :param  validator check if item is valid
    """
    guid = None
    if is_valid_guid(val):
        guid = val
    elif validator(val):
        guid = val.guid
    return not guid is None and len(func.take(lambda o: o.guid == guid, getattr(obj, name, []))) > 0


def pbxobj_add_list_value(obj, name, val, validator, index=None):
    """"
    add value 'val' to attribute 'name' of  pbxobject 'obj'.
    the attribute value is list of pbxobjects
    :param  obj     pbxobject
    :param  name    pbxattribute name
    :param  val     value(pbxobject or guid) to remove
    :param  validator check if item is valid
    :param  index   the index of val to add
    """
    if pbxobj_has_list_value(obj, name, val, validator):
        return

    if not validator(val):
        raise ValueError(\
            u'{obj} invalid {attr}: {v}'.format(obj=obj, attr=name[len(pbxconsts.PBX_ATTR_PREFIX):], v=val))

    obj._xcproj.add_object(val)
    if index is None:
        getattr(obj, name).append(val)
    else:
        getattr(obj, name).insert(index, val)
    val.add_referrer(obj)

def pbxobj_remove_list_value(obj, name, val, validator):
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
        attrval = getattr(obj, name)
        for o in list(attrval):
            if guid == o.guid:
                attrval.remove(o)
                o.remove_referrer(obj)

def validate_dependent_object(owner, ref_attr, throw_exception=False, issues=None):
    """
    validate the dependent object, 
    """
    from xcodeproj.pbxproj import baseobject
    refobj = getattr(owner, ref_attr, None)
    if refobj is None:
        msg = u'{attr} is None'.format(attr=ref_attr[len(pbxconsts.PBX_ATTR_PREFIX):])
        if throw_exception:
            raise baseobject.PBXValidationError(msg)
        elif not issues is None:
            issues.append(msg)
    try:
        refobj.validate()
    except Exception as e:
        if isinstance(e, baseobject.PBXValidationError):
            if throw_exception:
                raise # throw through
            if not issues is None:
                issues.append(u'invalid {attr}: {ex}'\
                    .format(attr=ref_attr[len(pbxconsts.PBX_ATTR_PREFIX):], ex=e))
        else:
            raise

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
    
    minetype, charset = get_file_info(filepath)
    if not minetype is None and minetype in pbxconsts.MIME_TO_FILETYPE:
        return pbxconsts.MIME_TO_FILETYPE[minetype]
    else:
        logger.warn(u'not PBXFileType for mimetype: %s' % mimetype)
        return None