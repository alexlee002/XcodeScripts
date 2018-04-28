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
from xcodeproj.pbxproj import abstract
from xcodeproj.pbxproj import pbxhelper
from xcodeproj.pbxproj import pbxconsts

class XcodeProj(abstract.PBXAbstract):
    """
    Attributes:
        __project_file_path     '.xcodeproj' path
        __pbxfile               'project.pbxproj'

    PBX Attributes:
        archiveVersion 
        objectVersion
        classes
        rootObject
    """

    def __init__(self):
        super(XcodeProj, self).__init__()
        self.__pbxfile = u'project.pbxproj'
        self.__objects = pbxobjects.PBXObjects()
        self.__project_file_path = None
        self.__plist_objects = None

    @staticmethod
    def create(project_dir, product_name, deployment_target, \
        product_type=pbxconsts.TARGET_PRODUCT_TYPE.app, \
        platform=pbxconsts.PLATFORM.ios, language=pbxconsts.LANGUAGE.objc):
        """
        create an empty project.
        :param project_dir:     where the .xcodeproj file located, 
                                eg: {project_dir}/{product_name}.xcodeproj
        :param product_name:    the .xcodeproj name
        """

        from xcodeproj.pbxproj import projhelper
        xcprojpath = os.path.abspath(os.path.join(project_dir, product_name+u'.xcodeproj'))
        
        xcproj = XcodeProj()
        xcproj.__project_file_path = xcprojpath
        xcproj.pbx_classes = {}
        xcproj.pbx_archiveVersion = pbxconsts.ARCHIVE_VERSION
        xcproj.pbx_objectVersion = pbxconsts.OBJECT_VERSION

        # create rootObject
        project = xcproj.new_object(u'PBXProject')
        xcproj.pbx_rootObject = project
        project.pbx_buildConfigurationList = projhelper.default_project_configuration_list(xcproj, \
            platform=platform, product_type=product_type, language=language)
        target = project.new_native_target(product_name, product_type=product_type, \
            platform=platform, language=language, deployment_target=deployment_target)

        main_group = xcproj.new_object(u'PBXGroup')
        project.pbx_mainGroup = main_group
        product_group = main_group.addgroup(name=u'Products')
        project.pbx_productRefGroup = product_group
        main_group.addgroup(name=u'Frameworks')
        return xcproj

    @staticmethod
    def load(xcprojpath, pbxprojfile=u'project.pbxproj'):
        """
        load and parse pbxproj file.
        :param xcprojpath:      path to ".xcodeproj".
        :param pbxprojfile:     default is 'project.pbxproj', 
                                you can specified another name if needed
        """
        xcprojpath = os.path.normpath(os.path.abspath(xcprojpath))

        projname, projext = os.path.splitext(os.path.basename(xcprojpath))
        if not projext == u'.xcodeproj' or not os.path.isdir(xcprojpath):
            logger.error(u'[XcodeProj] Illegal Xcode Project path: "%s"' % xcprojpath)
            sys.exit(1)

        pbxproj_path = os.path.join(xcprojpath, pbxprojfile)
        if not os.path.isfile(pbxproj_path):
            logger.error(u'[XcodeProj] Illegal Project file: "%s"' % pbxproj_path)
            sys.exit(1)

        import subprocess
        cmd_args = (
            u'/usr/bin/plutil',
            u'-convert', u'json',
            u'-o', u'-',
            pbxproj_path
        )
        p = subprocess.Popen(cmd_args, stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if not p.returncode == 0:
            logger.error(u'[XcodeProj] Incomprehensible file: %s; %s' % (pbxproj_path, stderr))
            sys.exit(1)

        import json
        plist_dict = json.loads(stdout)
        if not func.isdict(plist_dict):
            logger.error(u'[XcodeProj] Bad format: %s; %s' % (pbxproj_path, stderr))
            sys.exit(1)

        # parse objects
        xcproj = XcodeProj()
        xcproj.__project_file_path = xcprojpath
        xcproj.__pbxfile = pbxprojfile

        xcproj.__parse(plist_dict)
        return xcproj

    def __parse(self, plist_dict):
        objects = plist_dict.pop(u'objects', None)
        self.__plist_objects = objects if func.isdict(objects) else None

        for k, v in plist_dict.items():
            plist_dict.pop(k)
            pbxkey = u'pbx_{name}'.format(name=k)
            if k == u'rootObject':
                v = self.get_object(v)
            setattr(self, pbxkey, v)

        if len(self.__plist_objects) > 0:
            logger.warn(u'[XcodeProj] isolate objects are not be parsed:\n\t{0}'\
                .format(u'\n\t'.join([u'{0}:{1}'.format(k, v.get(u'isa')) \
                    for k, v in self.__plist_objects.items()])))
        self.__plist_objects = None # process complete


    def __validate_files(self):
        def __remove_multi_owners(obj, resolved):
            for owner in obj.owners().values():
                owner.validate()
            owners = sorted(obj.owners().values(), key=lambda o:o.guid)
            if len(owners) > 1:
                owners.pop(0)
                for owner in owners:
                    obj.remove_referrer(owner)
                resolved.append(u'{f} remove redundant owners:\n\t{o}'\
                    .format(f=obj, o=u'\n\t'.join(map(lambda o:str(o), owners))))

        def __resolve_isolate_files(isa, resolved):
            isolate_files = []
            if isa in self.__objects:
                for file in self.__objects[isa].values():
                    if len(file.owners()) == 0:
                        isolate_files.append(file)
                        self.remove_object(file)

            if len(isolate_files) > 0:
                resolved.append(u'remove isolate files:\n\t{fs}'\
                    .format(fs=u'\n\t'.join([str(f) for f in isolate_files])))

        def __deduplicate_files(isa, resolved):
            if not isa in self.__objects:
                return
            import itertools
            grouped_files = sorted(self.__objects[isa].values(), key=lambda f: f.realpath())
            grouped_files = itertools.groupby(grouped_files, lambda f:f.realpath())
            for path, files in grouped_files:
                files = list(files)
                reserved = files.pop(0)
                if len(files) > 0:
                    for f in files:
                        reserved.replace(f)
                    resolved.append(u'merge duplicate files to {f}:\n\t{d}'\
                        .format(f=reserved, d=u'\n\t'.join(map(lambda o:str(o), files))))

                __remove_multi_owners(reserved, resolved) 
        # end of __deduplicate_files

        def __verify_groups(resolved):
            for obj in self.__objects[u'PBXGroup'].values():
                __remove_multi_owners(obj, resolved)
        # end of __verify_groups

        resolved=[]
        __resolve_isolate_files(u'PBXFileReference', resolved)
        __resolve_isolate_files(u'PBXReferenceProxy', resolved)

        __deduplicate_files(u'PBXFileReference', resolved)
        __deduplicate_files(u'PBXReferenceProxy', resolved)
        __verify_groups(resolved)
        if len(resolved) > 0:
            logger.verbose(u'========= {obj} ========={sep}{msg}{sep}'\
                .format(obj=self.project_dir(), msg=os.linesep.join(resolved), sep=os.linesep))


    def validate(self):
        """
        validate project's objects,  remove the invalid objects.
        canonize the pbxproj by removing duplcated objects, resolve the object tree.
        """
        self.__validate_files()

        while self.need_validate():
            for guid, obj in self.__objects.guid_items():
                try:
                    obj.validate()
                except PBXValidationError as e:
                    self.remove_object(obj)
        
        isolate_objs = [obj for guid, obj in self.__objects.guid_items() \
            if not obj == self.pbx_rootObject and len(obj.referrers()) == 0]
        if len(isolate_objs) > 0:
            logger.warn(u'[XcodeProj] isolate objects:\n\t{0}'\
                .format(u'\n\t'.join([str(o) for o in isolate_objs])))

    def need_validate(self):
        """
        return True if there is any object need validate.
        """
        return len(func.take(lambda o: o[1].isdirty() and len(o[1].referrers()) > 0, \
            self.__objects.guid_items())) > 0

    def save(self, tofile=None):
        """
        save project objects to file.
        :param tofile:  the path of file to write to.
        """
        if self.__project_file_path is None:
            logger.error(u'project file path is not set!')
            return

        if not os.path.isdir(self.__project_file_path):
            os.makedirs(self.__project_file_path)

        buff = []
        self.write(buff)
        if len(buff) == 0:
            return

        bakup_file = None
        if tofile is None:
            tofile = os.path.join(self.__project_file_path, self.__pbxfile)
            if os.path.isfile(tofile):
                bakup_file = tofile + u'.bak'
                os.rename(tofile, bakup_file)

        try:
            with open(tofile, u'w') as fp:
                fp.writelines(u''.join(buff).encode('utf-8'))
        except Exception as e:
            logger.error(u'[XcodeProj] Can not write to file "{tofile}"; error:"{error}"'\
                .format(tofile=tofile, error=e))
            if not bakup_file is None and os.path.isfile(bakup_file):
                os.rename(bakup_file, tofile)
                logger.info(u'[XcodeProj] restore {pbxfile}'.format(pbxfile=self.__pbxfile))
        else:
            # write correctly, delete backup file
            if not bakup_file is None and os.path.isfile(bakup_file):
                os.remove(bakup_file)

    def pbxdict(self):
        plist_dic = super(XcodeProj, self).pbxdict()
        plist_dic[u'objects'] = self.__objects
        return plist_dic

    def write(self, buff, identstr=u''):
        """
        print objects in pbxproj's plist format
        """
        # plist_dic = {k[len(pbxconsts.PBX_ATTR_PREFIX):]:v \
        #     for k, v in self.__dict__.items() if func.hasprefix(k, pbxconsts.PBX_ATTR_PREFIX)}
        # plist_dic[u'objects'] = self.__objects
        plist_dic = self.pbxdict()

        self.safely_write(buff, u'// !$*UTF8*$!')
        self.safely_write(buff, os.linesep)
        self.safely_write(buff, u'{')
        self.safely_write(buff, os.linesep)
        for k, v in sorted(plist_dic.items(), key=lambda o: o[0]):
            if k == u'objects':
                self.safely_write(buff, u'\tobjects = {{{sep}'.format(sep=os.linesep))
                v.write(buff, u'\t')
                self.safely_write(buff, u'\t}};{sep}'.format(sep=os.linesep))
            else:
                self._print_kv(buff, k, v, u'\t', singleline=False)
        self.safely_write(buff, u'}')

    def get_object(self, guid):
        """ 
        get pbx-object with specified guid
        :param guid:    the object's guid
        """
        obj = self.__objects.get(guid)
        if obj is None and not self.__plist_objects is None:
            # self.__plist_objects is None indicates that the parsing process is finished
            objdict = self.__plist_objects.pop(guid, None)
            if func.isdict(objdict):
                objcls = objdict.pop(u'isa', None)
                if not objcls is None:
                    try:
                        obj = self.__new_object(objcls, guid)
                        obj.parse(objdict)
                    except Exception as e:
                        logger.warn(e)
                        raise
                else:
                    logger.warn(u'[XcodeProj] Bad format. "isa" not found for object:{guid}'\
                        .format(guid=guid))
            elif not objdict is None:
                logger.warn(\
                    u'[XcodeProj] {guid} invalid object dict:{dic}'.format(guid=guid, dic=objdict))
        return obj

    def objects(self):
        """ return all pbx-objects """
        return self.__objects

    def __new_object(self, isa, guid=None):
        def __new_guid():
            import uuid
            from xcodeproj.pbxproj import pbxconsts

            for x in xrange(1,10):
                guid = unicode(uuid.uuid1().hex[0:pbxconsts.REFID_LEN].upper())
                if not guid in self.__objects:
                    return guid
                raise ValueError(u'[XcodeProj] Failed to generate valid guid!')
        # end of __new_guid
        module = __import__('xcodeproj.pbxproj.objects', fromlist=['*'])
        if hasattr(module, isa):
            if guid is None:
                guid = __new_guid()
            obj = getattr(module, isa)(self, guid)
            self.add_object(obj)
            return obj
        raise ValueError(u'[XcodeProj] Unknown object type:"{isa}"'.format(isa=isa))

    def new_object(self, isa):
        """ create new object with 'isa' and add to the project """
        try:
            return self.__new_object(isa)
        except Exception as e:
            logger.warn(func.exception_msg(e))
            raise
            return None

    def add_object(self, obj):
        """ add object to project """
        assert isinstance(obj, baseobject.PBXBaseObject)
        assert obj.project() == self
        res = self.get_object(obj.guid)
        if res == obj:
            # obj._xcproj = self
            return
        elif res is None: # or res.isa == obj.isa:
            self.__objects[obj.guid] = obj
            # obj._xcproj = self
        else:
            raise ValueError(\
                u'object "{new}" conflict with existed object "{old}"'.format(new=obj, old=res))

    def remove_object(self, obj):
        """ remove object from project """
        if pbxhelper.is_valid_guid(obj):
            obj = get_object(obj)

        if isinstance(obj, baseobject.PBXBaseObject):
            for guid, refer in obj.referrers().items():
                obj.remove_referrer(refer)
            self.__objects.pop(obj.guid)
            # obj._xcproj = None

    def buildsettings(self, name, target=None, config=None, default=None):
        """ 
        get the project's common build settings,
        :param name:    the name of build setting
        :param target:  the 'PBXTarget' or 'guid' or 'target name', 
                        from which to get the build setting
        :param config:  the 'XCBuildConfiguration' or 'guid' or 'config name'
        """
        if name in [u'PROJECT_DIR', u'SRCROOT', u'SOURCE_ROOT']:
            return self.project_dir()
        elif name == u'PROJECT_NAME':
            return self.project_name()
        elif name == u'PROJECT_FILE_PATH':
            return self.__project_file_path
        else:

            def __get_setting(config, name, cfglist, default):
                cfg = config
                if cfg is None:
                    cfg = cfglist.defaultConfiguration() if not cfglist is None else None
                elif pbxhelper.is_valid_guid(config):
                    cfg = self.get_object(config)
                elif func.isstr(config):
                    cfg = cfglist.getconfig(config) if not cfglist is None else None
                if not isinstance(cfg, config_imp.XCBuildConfiguration):
                    return None
                return cfg.get_build_setting(name, default=default)
            # end of __get_setting()

            if not target is None:
                from xcodeproj.pbxproj.objects import target as target_imp
                from xcodeproj.pbxproj.objects import config as config_imp
                
                tobj = target
                if tobj is None:
                    tobj = func.get_list_item(self.pbx_rootObject.pbx_targets, 0)
                elif pbxhelper.is_valid_guid(target):
                    tobj = self.get_object(target)
                elif func.isstr(target):
                    tobj = self.get_target(target)
                if not isinstance(tobj, target_imp.PBXTarget):
                    return None
                
                return __get_setting(config, name, tobj.pbx_buildConfigurationList, default)
            elif not config is None:
                return __get_setting(config, name, None, default)

        if os.getenv(u'PROJECT_FILE_PATH') == self.__project_file_path:
            return os.getenv(name) 
        return None

    def project_name(self):
        """ return the name of '.xcodeproj' """
        if self.__project_file_path is None:
            return None
        return os.path.splitext(os.path.basename(self.__project_file_path))[0]

    def project_dir(self):
        """ return the base dir of '.xcodeproj' """
        if self.__project_file_path is None:
            return None
        path = os.path.dirname(self.__project_file_path)
        if not self.pbx_rootObject is None and not self.pbx_rootObject.pbx_projectDirPath is None:
            return os.path.join(path, self.pbx_rootObject.pbx_projectDirPath)
        return path

    def main_group(self):
        """ return the project's main group """
        return self.pbx_rootObject.pbx_mainGroup

    def get_target(self, name):
        """ return target object with specified name """
        if self.pbx_rootObject is None:
            return None
        return self.pbx_rootObject.gettarget(name)

    def fileref_for_path(self, abspath):
        """ return the filereferece object with abspath in disk """
        return func.get_list_item(\
            func.take(lambda o: o.realpath() == abspath, \
                self.__objects.get(u'PBXFileReference', default=dict()).values()), 0)

    def get_variant_group(self, abspath, name):
        """ return the variant group in specified path and name """
        return func.get_list_item(\
            func.take(lambda o: o.realpath() == abspath and o.pbx_name == name, \
                self.__objects.get(u'PBXVariantGroup', default=dict()).values()), 0)

    def addfile(self, path, group, target=None, copy=False, settings=None):
        """
        add file to 'group', and create build file for this file and add to buildphase of target.
        if path is a dir,  recursively add all subfiles and subdirs.
        """
        from xcodeproj.pbxproj import projhelper
        projhelper.addfile(self, path, group, target, copy, settings)
