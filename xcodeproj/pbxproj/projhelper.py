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
from xcodeproj.pbxproj import baseobject
from xcodeproj.pbxproj import pbxobjects
from xcodeproj.pbxproj import pbxhelper
from xcodeproj.pbxproj import pbxconsts
from xcodeproj.pbxproj import pbxpath
from xcodeproj.pbxproj import pbxproj

import shutil

def addfile(xcproj, path, groupobj, targetobj=None, copy=False, settings=None):
    """
    add file/directory at 'filepath' to 'groupobj', 
    and create buildfile for files and then add to 'targetobj'
    :param xcproj:      the xcodeproj
    :param targetobj:   the target to add buildfile for files in filepath
    :param groupobj:    the group where files added to.
    :param copy:        if True and if filepath is not in PROJECT_DIR, copy files to PROJECT_DIR
    :param settings:    the build settings for build file
    """

    def __addfile(xcproj, targetobj, parentgroup, filepath, settings=None):
        """ add single file """
        if func.hasprefix(os.path.basename(filepath), u'.'):
            return

        fileref = None
        dirname, dirext = os.path.splitext(os.path.basename(os.path.dirname(filepath)))
        if dirext == u'.lproj':
            # create variant group
            group_name = os.path.basename(filepath)
            group_path = os.path.abspath(os.path.dirname(os.path.dirname(filepath)))
            vgroup = parentgroup.add_variant_group(group_path, group_name)
            lproj_ref = vgroup.addfile(filepath)
            fileref = vgroup
        else:
            # create file reference and add to group
            fileref = parentgroup.addfile(filepath)

        if not targetobj is None and not fileref is None and fileref.isa == u'PBXFileReference':
            # create buildfile if not header file
            bpisa = pbxhelper.buildphase_for_filetype(fileref.filetype())
            if not bpisa == u'PBXHeadersBuildPhase':
                bp = targetobj.get_build_phase(bpisa, create=True)
                bp.add_file_reference(fileref, settings=settings)
    # end of __addfile()

    def __recursively_add(xcproj, targetobj, parentgroup, path, settings):
        if func.hasprefix(os.path.basename(path), u'.'):
            return

        if os.path.isfile(path):
            __addfile(xcproj, targetobj, parentgroup, path, settings)
        elif os.path.isdir(path):
            dirext = os.path.splitext(path)[1]
            filetype = pbxconsts.FILETYPE_BY_EXT.get(dirext)
            if not filetype is None and filetype in pbxconsts.FOLDER_FILE_TYPE:
                __addfile(xcproj, targetobj, parentgroup, path, settings)
            else:
                subgroup = parentgroup.addgroup(path)
                for fn in os.listdir(path):
                    __recursively_add(xcproj, targetobj, subgroup, os.path.join(path, fn), settings)
    # end of __recursively_add

    filepath = os.path.abspath(filepath)
    if not pbxpath.issubpath(filepath, xcproj.project_dir()) and copy:
        dstpath = os.path.join(groupobj.realpath(), os.path.basename(filepath))
        if os.path.isdir(filepath):
            shutil.copytree(filepath, dstpath)
        elif os.path.isfile(filepath):
            dstdir = os.path.dirname(dstpath)
            if not os.path.isdir(dstdir):
                os.makedirs(dstdir)
            shutil.copy2(filepath, dstpath)
        filepath = dstpath

    __recursively_add(xcproj, targetobj, groupobj, filepath, settings)


def default_project_configuration(config, platform=pbxconsts.PLATFORM.ios, \
    product_type=pbxconsts.TARGET_PRODUCT_TYPE.app, language=pbxconsts.LANGUAGE.objc):
    """
    return default build settings for project
    """
    common_settings = {
        u'ALWAYS_SEARCH_USER_PATHS':                u'NO',
        u'CLANG_ANALYZER_NONNULL':                  u'YES',
        u'CLANG_ANALYZER_NUMBER_OBJECT_CONVERSION': u'YES_AGGRESSIVE',
        u'CLANG_CXX_LANGUAGE_STANDARD':             u'gnu++14',
        u'CLANG_CXX_LIBRARY':                       u'libc++',
        u'CLANG_ENABLE_MODULES':                    u'YES',
        u'CLANG_ENABLE_OBJC_ARC':                   u'YES',
        u'CLANG_ENABLE_OBJC_WEAK':                  u'YES',
        u'CLANG_WARN__DUPLICATE_METHOD_MATCH':      u'YES',
        u'CLANG_WARN_BLOCK_CAPTURE_AUTORELEASING':  u'YES',
        u'CLANG_WARN_BOOL_CONVERSION':              u'YES',
        u'CLANG_WARN_COMMA':                        u'YES',
        u'CLANG_WARN_CONSTANT_CONVERSION':          u'YES',
        u'CLANG_WARN_DEPRECATED_OBJC_IMPLEMENTATIONS': u'YES',
        u'CLANG_WARN_DIRECT_OBJC_ISA_USAGE':        u'YES_ERROR',
        u'CLANG_WARN_DOCUMENTATION_COMMENTS':       u'YES',
        u'CLANG_WARN_EMPTY_BODY':                   u'YES',
        u'CLANG_WARN_ENUM_CONVERSION':              u'YES',
        u'CLANG_WARN_INFINITE_RECURSION':           u'YES',
        u'CLANG_WARN_INT_CONVERSION':               u'YES',
        u'CLANG_WARN_NON_LITERAL_NULL_CONVERSION':  u'YES',
        u'CLANG_WARN_OBJC_IMPLICIT_RETAIN_SELF':    u'YES',
        u'CLANG_WARN_OBJC_LITERAL_CONVERSION':      u'YES',
        u'CLANG_WARN_OBJC_ROOT_CLASS':              u'YES_ERROR',
        u'CLANG_WARN_RANGE_LOOP_ANALYSIS':          u'YES',
        u'CLANG_WARN_STRICT_PROTOTYPES':            u'YES',
        u'CLANG_WARN_SUSPICIOUS_MOVE':              u'YES',
        u'CLANG_WARN_UNGUARDED_AVAILABILITY':       u'YES_AGGRESSIVE',
        u'CLANG_WARN_UNREACHABLE_CODE':             u'YES',
        u'COPY_PHASE_STRIP':                        u'NO',
        u'ENABLE_STRICT_OBJC_MSGSEND':              u'YES',
        u'GCC_C_LANGUAGE_STANDARD':                 u'gnu11',
        u'GCC_NO_COMMON_BLOCKS':                    u'YES',
        u'GCC_WARN_64_TO_32_BIT_CONVERSION':        u'YES',
        u'GCC_WARN_ABOUT_RETURN_TYPE':              u'YES_ERROR',
        u'GCC_WARN_UNDECLARED_SELECTOR':            u'YES',
        u'GCC_WARN_UNINITIALIZED_AUTOS':            u'YES_AGGRESSIVE',
        u'GCC_WARN_UNUSED_FUNCTION':                u'YES',
        u'GCC_WARN_UNUSED_VARIABLE':                u'YES',
        u'PRODUCT_NAME':                            u'$(TARGET_NAME)',
    }

    if config == pbxconsts.CONFIG.release:
        common_settings.update({
            u'DEBUG_INFORMATION_FORMAT':    u'dwarf-with-dsym',
            u'ENABLE_NS_ASSERTIONS':        u'NO',
            u'MTL_ENABLE_DEBUG_INFO':       u'NO',
        })

    elif config == pbxconsts.CONFIG.debug:
        common_settings.update({
            u'DEBUG_INFORMATION_FORMAT':    u'dwarf',
            u'ENABLE_TESTABILITY':          u'YES',
            u'GCC_DYNAMIC_NO_PIC':          u'NO',
            u'GCC_OPTIMIZATION_LEVEL':      u'0',
            u'GCC_PREPROCESSOR_DEFINITIONS': (u'DEBUG=1', u'$(inherited)'),
            u'MTL_ENABLE_DEBUG_INFO':       u'YES',
            u'ONLY_ACTIVE_ARCH': u'YES',
        })
    return common_settings


def default_project_configuration_list(xcproj, platform=pbxconsts.PLATFORM.ios, \
    product_type=pbxconsts.TARGET_PRODUCT_TYPE.app, language=pbxconsts.LANGUAGE.objc):
    """
    create default XCConfigurationList object for project
    """
    cfglist = xcproj.new_object(u'XCConfigurationList')
    cfglist.pbx_defaultConfigurationName = pbxconsts.CONFIG.release

    for cfgname in (pbxconsts.CONFIG.debug, pbxconsts.CONFIG.release):
        cfg = xcproj.new_object(u'XCBuildConfiguration')
        cfg.pbx_name = cfgname
        cfg.pbx_buildSettings = default_project_configuration(cfgname, \
            platform, product_type, language)
        cfglist.addconfig(cfg)

    return cfglist


def default_target_configuration(config, platform=pbxconsts.PLATFORM.ios, \
    product_type=pbxconsts.TARGET_PRODUCT_TYPE.app, language=pbxconsts.LANGUAGE.objc, \
    deployment_target=None):
    """
    return default build settings for target
    """
    def __set_platform(settings, platform, deployment_target):
        if platform == pbxconsts.PLATFORM.ios:
            settings.update({
                u'SDKROOT':                    u'iphoneos',
                u'IPHONEOS_DEPLOYMENT_TARGET': deployment_target,
                u'CLANG_ENABLE_OBJC_WEAK':     u'NO' if float(deployment_target) < 5 else 'YES'
            })

        elif platform == pbxconsts.PLATFORM.osx:
            settings.update({
                u'SDKROOT':                  u'macosx',
                u'MACOSX_DEPLOYMENT_TARGET': deployment_target,
                u'CLANG_ENABLE_OBJC_WEAK':   u'NO' if float(deployment_target) < 10.7 else 'YES'
            })

        elif platform == pbxconsts.PLATFORM.watchos:
            settings.update({
                u'SDKROOT':                   u'watchos',
                u'WATCHOS_DEPLOYMENT_TARGET': deployment_target,
            })
        elif platform == pbxconsts.PLATFORM.tvos:
            settings.update({
                u'SDKROOT':                u'appletvos',
                u'TVOS_DEPLOYMENT_TARGET': deployment_target,
            })


    def __set_framework_settings(settings, platform, language):
        settings.update({
            u'CURRENT_PROJECT_VERSION':     u'1',
            u'DEFINES_MODULE':              u'YES',
            u'DYLIB_COMPATIBILITY_VERSION': u'1',
            u'DYLIB_CURRENT_VERSION':       u'1',
            u'DYLIB_INSTALL_NAME_BASE':     u'@rpath',
            u'INSTALL_PATH':                u'$(LOCAL_LIBRARY_DIR)/Frameworks',
            u'PRODUCT_NAME':                u'$(TARGET_NAME:c99extidentifier)',
            u'SKIP_INSTALL':                u'YES',
            u'VERSIONING_SYSTEM':           u'apple-generic',
        })

        if platform == pbxconsts.PLATFORM.ios:
            settings[u'LD_RUNPATH_SEARCH_PATHS'] = \
                u'$(inherited) @executable_path/Frameworks @loader_path/Frameworks'
            settings[u'TARGETED_DEVICE_FAMILY']  = u'1,2'
        elif platform == pbxconsts.PLATFORM.osx:
            settings[u'COMBINE_HIDPI_IMAGES']    = u'YES'
            settings[u'FRAMEWORK_VERSION']       = u'A'
            settings[u'LD_RUNPATH_SEARCH_PATHS'] = \
                u'$(inherited) @executable_path/../Frameworks @loader_path/Frameworks'
        elif platform == pbxconsts.PLATFORM.watchos:
            settings[u'APPLICATION_EXTENSION_API_ONLY'] = u'YES'
            settings[u'LD_RUNPATH_SEARCH_PATHS']        = \
                u'$(inherited) @executable_path/Frameworks @loader_path/Frameworks'
            settings[u'TARGETED_DEVICE_FAMILY'] = u'4'
        elif platform == pbxconsts.PLATFORM.tvos:
            settings[u'LD_RUNPATH_SEARCH_PATHS'] = \
                u'$(inherited) @executable_path/Frameworks @loader_path/Frameworks'
            settings[u'TARGETED_DEVICE_FAMILY']  = u'3'

        if language == pbxconsts.LANGUAGE.swift:
            settings[u'DEFINES_MODULE'] = u'YES'

    def __set_static_lib_settings(settings, platform, language):
        if platform == pbxconsts.PLATFORM.ios:
            settings[u'SKIP_INSTALL']           = u'YES'
            settings[u'TARGETED_DEVICE_FAMILY'] = u'1,2'
        elif platform == pbxconsts.PLATFORM.osx:
            settings[u'EXECUTABLE_PREFIX']      = u'lib'
            settings[u'SKIP_INSTALL']           = u'YES'
        elif platform == pbxconsts.PLATFORM.tvos:
            settings[u'SKIP_INSTALL']           = u'YES'
            settings[u'TARGETED_DEVICE_FAMILY'] = u'3'
        elif platform == pbxconsts.PLATFORM.watchos:
            settings[u'SKIP_INSTALL']           = u'YES'
            settings[u'TARGETED_DEVICE_FAMILY'] = u'4'

    def __set_dylib_settings(settings, platform, language):
        if platform == pbxconsts.PLATFORM.osx:
            settings[u'DYLIB_COMPATIBILITY_VERSION'] = u'1'
            settings[u'DYLIB_CURRENT_VERSION']       = u'1'
            settings[u'EXECUTABLE_PREFIX']           = u'lib'
            settings[u'SKIP_INSTALL']                = u'YES'

    def __set_app_settings(settings, platform, language):
        if platform == pbxconsts.PLATFORM.ios:
            settings[u'LD_RUNPATH_SEARCH_PATHS'] = u'$(inherited) @executable_path/Frameworks'
            settings[u'TARGETED_DEVICE_FAMILY']  = u'1,2'
        elif platform == pbxconsts.PLATFORM.osx:
            settings[u'COMBINE_HIDPI_IMAGES'] = u'YES'
            settings[u'LD_RUNPATH_SEARCH_PATHS'] = u'$(inherited) @executable_path/../Frameworks'
        elif platform == pbxconsts.PLATFORM.tvos:
            settings[u'ASSETCATALOG_COMPILER_APPICON_NAME']     = u'App Icon & Top Shelf Image'
            settings[u'ASSETCATALOG_COMPILER_LAUNCHIMAGE_NAME'] = u'LaunchImage'
            settings[u'LD_RUNPATH_SEARCH_PATHS'] = u'$(inherited) @executable_path/Frameworks'
            settings[u'TARGETED_DEVICE_FAMILY']  = u'3'
            if language == pbxconsts.LANGUAGE.swift:
                settings[u'ALWAYS_EMBED_SWIFT_STANDARD_LIBRARIES'] = u'YES'
        elif platform == pbxconsts.PLATFORM.watchos:
            settings[u'SKIP_INSTALL']           = u'YES'
            settings[u'TARGETED_DEVICE_FAMILY'] = u'4'

    def __set_bundle_settings(settings, platform, language):
        settings[u'WRAPPER_EXTENSION'] = u'bundle'
        settings[u'SKIP_INSTALL']      = u'YES'
        if platform == pbxconsts.PLATFORM.ios:
            settings[u'SDKROOT']       = u'iphoneos'
        elif platform == pbxconsts.PLATFORM.osx:
            settings[u'COMBINE_HIDPI_IMAGES'] = u'YES'
            settings[u'INSTALL_PATH']  = u'$(LOCAL_LIBRARY_DIR)/Bundles'
            settings[u'SDKROOT']       = u'macosx'

    def __common_settings(platform, language, deployment_target):
        settings = {}
        __set_platform(settings, platform, deployment_target)

        if pbxconsts.TARGET_PRODUCT_TYPE.app:
            __set_app_settings(settings, platform, language)
        if pbxconsts.TARGET_PRODUCT_TYPE.framework:
            __set_framework_settings(settings, platform, language)
        if pbxconsts.TARGET_PRODUCT_TYPE.static_lib:
            __set_static_lib_settings(settings, platform, language)
        if pbxconsts.TARGET_PRODUCT_TYPE.bundle:
            __set_bundle_settings(settings, platform, language)
        if pbxconsts.TARGET_PRODUCT_TYPE.dylib:
            __set_dylib_settings (settings, platform, language)
        return settings
    #end of internal funcs
 
    settings = __common_settings(platform, language, deployment_target)
    if config == pbxconsts.CONFIG.release:
        settings[u'VALIDATE_PRODUCT'] = u'YES'
        if language == pbxconsts.LANGUAGE.swift:
            settings[u'SWIFT_OPTIMIZATION_LEVEL'] = u'-Owholemodule'
    elif config == pbxconsts.CONFIG.debug:
        if language == pbxconsts.LANGUAGE.swift:
            settings[u'SWIFT_OPTIMIZATION_LEVEL']            = u'-Onone'
            settings[u'SWIFT_ACTIVE_COMPILATION_CONDITIONS'] = u'DEBUG'

    return settings


def default_target_configuration_list(xcproj, platform=pbxconsts.PLATFORM.ios, \
    product_type=pbxconsts.TARGET_PRODUCT_TYPE.app, language=pbxconsts.LANGUAGE.objc, \
    deployment_target=None):
    """
    create default XCConfigurationList object for target
    """
    
    cfglist = xcproj.new_object(u'XCConfigurationList')
    cfglist.pbx_defaultConfigurationName = pbxconsts.CONFIG.release

    config_names = (pbxconsts.CONFIG.debug, pbxconsts.CONFIG.release)
    if not xcproj.pbx_rootObject is None:
        proj_cfglist = xcproj.pbx_rootObject.pbx_buildConfigurationList
        cfglist.pbx_defaultConfigurationName = proj_cfglist.pbx_defaultConfigurationName
        if not proj_cfglist is None:
            config_names = tuple([c.pbx_name for c in proj_cfglist.pbx_buildConfigurations])

    for cfgname in config_names:
        cfg = xcproj.new_object(u'XCBuildConfiguration')
        cfg.pbx_name = cfgname
        cfg.pbx_buildSettings = default_target_configuration(cfgname, \
            platform, product_type, language, deployment_target)
        cfglist.addconfig(cfg)
    return cfglist
