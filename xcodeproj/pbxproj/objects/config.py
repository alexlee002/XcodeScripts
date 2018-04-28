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
from xcodeproj.pbxproj import pbxpath
from xcodeproj.pbxproj import pbxhelper
from xcodeproj.utils import func
from xcodeproj.utils import logger


ARRAY_SETTINGS = (
    u'ALTERNATE_PERMISSIONS_FILES',
    u'ARCHS',
    u'BUILD_VARIANTS',
    u'EXCLUDED_SOURCE_FILE_NAMES',
    u'FRAMEWORK_SEARCH_PATHS',
    u'GCC_PREPROCESSOR_DEFINITIONS',
    u'GCC_PREPROCESSOR_DEFINITIONS_NOT_USED_IN_PRECOMPS',
    u'HEADER_SEARCH_PATHS',
    u'INFOPLIST_PREPROCESSOR_DEFINITIONS',
    u'LIBRARY_SEARCH_PATHS',
    u'OTHER_CFLAGS',
    u'OTHER_CPLUSPLUSFLAGS',
    u'OTHER_LDFLAGS',
    u'REZ_SEARCH_PATHS',
    u'SECTORDER_FLAGS',
    u'WARNING_CFLAGS',
    u'WARNING_LDFLAGS'
)

class XCBuildConfiguration(baseobject.PBXBaseObject):
    """
    Build Configurations, 

    owner:    XCConfigurationList.  
    relative:    many to many

    bpx-attr:
        baseConfigurationReference  PBXFileReference    nullable
        buildSettings               dict                nonnull, default {}
        name                        str                 nonnull?
    """
    def __init__(self, xcproj, guid):
        super(XCBuildConfiguration, self).__init__(xcproj, guid)
        self.pbx_buildSettings = dict()

    def __setattr__(self, name, value):
        if name == u'pbx_baseConfigurationReference':
            pbxhelper.pbxobj_set_pbxobj_attr(self, XCBuildConfiguration, name, value, \
                self.is_valid_base_config_ref)
        elif name == u'pbx_buildSettings':
            self.__set_build_settings(value)
        else:
            super(XCBuildConfiguration, self).__setattr__(name, value)

    def __set_build_settings(self, value):
        if func.isdict(value):
            super(XCBuildConfiguration, self).__setattr__(u'pbx_buildSettings', value)
        else:
            logger.error(u'{0} illegal buildSettings:{1}'.format(self, value))

    def is_valid_base_config_ref(self, obj):
        """ check if obj is valid baseConfigurationReference value """
        return isinstance(obj, baseobject.PBXBaseObject) and obj.isa == 'PBXFileReference'

    def _accepted_owner(self, obj):
        """ override """
        return isinstance(obj, baseobject.PBXBaseObject) \
            and obj.isa == 'XCConfigurationList' and obj.hasconfig(self)

    def allow_multi_owners(self):
        """ override """
        return True

    def comment(self):
        """ override """
        return self.pbx_name

    def get_build_setting(self, name, default=None):
        """ return build setting for 'name' """
        return self.pbx_buildSettings.get(name, default)

    def set_build_setting(self, name, value):
        """ set setting value for 'name' """
        assert not name is None

        if value is None:
            self.remove_build_setting(name)
        else:
            self.pbx_buildSettings[name] = value

    def add_str_build_settings(self, name, value, seperator=' '):
        """
        add values to an existed settings. If the value is already exists, ignore.
        The value of setting is a str, eg: 
            VALID_ARCHS = "armv7 arm64";

        examples:
            add_str_build_settings('VALID_ARCHS', 'armv7s') => VALID_ARCHS = "armv7 arm64 armv7s";
    
            add_str_build_settings('VALID_ARCHS', ['i386', 'x86_64']) => 
                VALID_ARCHS = "armv7 arm64 i386 x86_64";

            add_str_build_settings('VALID_ARCHS', ['armv7s', 'arm64']) => 
                VALID_ARCHS = "armv7 arm64 armv7s";
        
        @param name     the setting name
        @param value    str or [str]
        @param seperator the seperator of items in setting value
        """
        arr = []
        if func.isseq(value):
            arr = list(value)
        elif not value is None:
            arr = [str(value)]

        settingval = self.get_build_setting(name, default='')
        for v in arr:
            if v is None:
                continue
            if settingval == v or func.hasprefix(settingval, v+seperator):
                continue
            if func.hassubfix(settingval, seperator+v):
                continue
            if seperator+v+seperator in settingval:
                continue

            settingval += seperator + v
        self.pbx_buildSettings[name] = settingval

    def add_array_build_settings(self, name, value):
        """
        add values to an existed settings. If the value is already exists, ignore.
        The value of setting is type of list, eg: 
            HEADER_SEARCH_PATHS = (
                /usr/include,
                /usr/local/include,
            };

        examples:
            add_array_build_settings('HEADER_SEARCH_PATHS', '../thirdparty')
            =>
            HEADER_SEARCH_PATHS = (
                /usr/include,
                /usr/local/include,
                ../thirdparty,
            };

            add_array_build_settings('HEADER_SEARCH_PATHS', \
                ['../thirdparty', '/usr/include'])
            =>
            HEADER_SEARCH_PATHS = (
                /usr/include,
                /usr/local/include,
                ../thirdparty,
            };
    
        @param name     the setting name
        @param value    str or [str]
        """
        settingval = self.get_build_setting(name, default=[])

        arr = []
        if func.isseq(value):
            arr.extend(value)
        else:
            arr.append(str(value))

        for v in arr:
            if not v in settingval:
                settingval.append(v)

        count = len(settingval)
        if count == 0:
            settingval = ''
        elif count == 1:
            settingval = str(settingval[0])

        self.pbx_buildSettings[name] = settingval

    def remove_build_setting(self, name):
        """ remove settings """
        self.pbx_buildSettings.pop(name)

    def deduplicate_paths(self, paths):
        """
        return deduplicate paths
        complete and normalize the paths, deduplicate the result
        """
        if func.isstr(paths):
            return paths

        if not func.isseq(paths):
            return u''

        path_dict = dict()
        for path in paths:
            normpath = path
            while func.hasprefix(normpath, '"') and func.hassubfix(normpath, '"'):
                normpath = normpath[1: len(normpath)-1]
            normpath = pbxpath.normalize_path(normpath)
            realpath = pbxpath.realpath(self.project(), normpath)

            if realpath in path_dict:
                continue
            if not func.hassubfix(realpath, os.sep+'**'):
                p = os.path.join(realpath, '**')
                if p in path_dict:
                    continue
            else:
                p = realpath[0: len(realpath) - len(os.sep+'**')]
                path_dict.pop(p, None)

            path_dict[realpath] = (path, normpath)

        return [p[1] for p in sorted(path_dict.values(), key=lambda p: paths.index(p[0]))]

    def _validate(self):
        resolved, issues = super(XCBuildConfiguration, self)._validate()

        def __resolve_paths(name):
            if name in self.pbx_buildSettings:
                self.pbx_buildSettings[name] = self.deduplicate_paths(self.pbx_buildSettings[name])

        __resolve_paths('FRAMEWORK_SEARCH_PATHS')
        __resolve_paths('HEADER_SEARCH_PATHS')
        __resolve_paths('LIBRARY_SEARCH_PATHS')

        return resolved, issues


class XCConfigurationList(baseobject.PBXBaseObject):
    """
    Configuration List for PBXProject, PBXNativeTarget. 

    owner:    PBXProject or PBXTarget
    relative:    one to one mapping.

    pbx-attr
        buildConfigurations         [XCBuildConfiguration], nonnull, default []
        defaultConfigurationIsVisible   int, nonnull, default 0
        defaultConfigurationName        str, nonnull
    """
    def __init__(self, xcproj, guid):
        super(XCConfigurationList, self).__init__(xcproj, guid)
        # pbx attributes
        self.pbx_buildConfigurations = [] # [guid]
        self.pbx_defaultConfigurationIsVisible = 0 # int

    def __setattr__(self, name, value):
        if name == u'pbx_buildConfigurations':
            pbxhelper.pbxobj_set_pbxlist_attr(self, XCConfigurationList, name, value, \
                self.is_valid_config)
        else:
            super(XCConfigurationList, self).__setattr__(name, value)

    def duplicate(self):
        """ override """
        obj = super(XCConfigurationList, self).duplicate()
        for attr, val in self.__dict__.items():
            if attr == u'pbx_buildConfigurations':
                for cfg in val:
                    obj.addfile(cfg.duplicate())
            elif func.hasprefix(attr, pbxconsts.PBX_ATTR_PREFIX):
                setattr(obj, attr, val)
        return obj

    def comment(self):
        """ override """
        owner = func.get_list_item(self.owners().values(), 0)
        projname = owner.displayname().encode('utf-8') if not owner is None else None
        return u'Build configuration list for {isa} "{name}"'.format(\
                    isa=u'(null)' if owner is None else owner.isa, \
                    name=u'(null)' if projname is None else projname)  

    def is_valid_config(self, config):
        """ check if 'config' is valid build configuration """
        return isinstance(config, XCBuildConfiguration)

    def _accepted_owner(self, obj):
        return self == obj.pbx_buildConfigurationList

    def allow_multi_owners(self):
        """ override """
        return False

    def _validate(self):
        resolved, issues = super(XCConfigurationList, self)._validate()

        pbxhelper.pbxobj_validate_pbxlist_attr(self, u'pbx_buildConfigurations', \
            self.is_valid_config, resolved=resolved, issues=issues)

        import itertools
        configs = sorted(self.pbx_buildConfigurations, key=lambda c: c.pbx_name)
        configs = itertools.groupby(configs, lambda c: c.pbx_name)
        for key, lst in configs:
            lst = list(lst)
            if len(lst) > 1:
                issues.append(u'duplicate config "{n}" found:\n\t{cfgs}'
                    .format(n=key, cfgs=u'\n\t'.join([str(o) for o in lst])))

        return resolved, issues

    def defaultConfiguration(self):
        """ 
        return build-configuration specified by defaultConfigurationName 
        or return the first one in configuration list
        """
        config = None
        if not self.pbx_defaultConfigurationName is None:
            config = self.getconfig(self.pbx_defaultConfigurationName)
        if config is None:
            config = func.get_list_item(self.pbx_buildConfigurations, 0)
        return config

    def getconfig(self, name, auto_create=False):
        """ return config with name, otherwise return None """
        if name is None:
            return None

        config = func.get_list_item(\
            func.take(lambda c: c.pbx_name == name, self.pbx_buildConfigurations), 0)
        if config is None and auto_create:
            config = self.project().new_object(u'XCBuildConfiguration')
            config.pbx_name = name
            self.addconfig(config)
        return config

    def addconfig(self, config, index=None):
        """
        add config to list
        """
        pbxhelper.pbxobj_add_pbxlist_value(self, u'pbx_buildConfigurations', config, \
            self.is_valid_config, index=index)

    def removeconfig(self, config=None, name=None):
        """ remove config from list """
        if not config is None:
            pbxhelper.pbxobj_remove_pbxlist_value(self, u'pbx_buildConfigurations', config, \
                self.is_valid_config)
        elif not name is None:
            idx = 0
            while idx < len(self.pbx_buildConfigurations):
                cfg = self.pbx_buildConfigurations[idx]
                if cfg.pbx_name == name:
                    self.pbx_buildConfigurations.pop(idx)
                    cfg.remove_referrer(self)
                else:
                    idx += 1


