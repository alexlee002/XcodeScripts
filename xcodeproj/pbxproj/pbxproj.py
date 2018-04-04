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

    @staticmethod
    def load(xcprojpath, pbxprojfile=u'project.pbxproj'):
        xcprojpath = os.path.normpath(os.path.abspath(xcprojpath))

        projname, projext = os.path.splitext(os.path.basename(xcprojpath))
        if not projext == u'.xcodeproj' or not os.path.isdir(xcprojpath):
            logger.error(u'Illegal Xcode Project path: "%s"' % xcprojpath)
            sys.exit(1)

        pbxproj_path = os.path.join(xcprojpath, pbxprojfile)
        if not os.path.isfile(pbxproj_path):
            logger.error(u'Illegal Project file: "%s"' % pbxproj_path)
            sys.exit(1)

        import subprocess
        p = subprocess.Popen([u'/usr/bin/plutil', u'-convert', u'json', u'-o', u'-', pbxproj_path], \
            stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if not p.returncode == 0:
            logger.error(u'Incomprehensible file: %s; %s' % (pbxproj_path, stderr))
            sys.exit(1)

        import json
        plist_dict = json.loads(stdout)
        if not func.isdict(plist_dict):
            logger.error(u'Bad format: %s; %s' % (pbxproj_path, stderr))
            sys.exit(1)

        # parse objects
        xcproj = XcodeProj()
        xcproj.__project_file_path = xcprojpath
        xcproj.__pbxfile = pbxprojfile
        xcproj.__objects = pbxobjects.PBXObjects()

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
                .format(u'\n\t'.join([u'{0}:{1}'.format(k, func.get_dict_val(v, u'isa')) \
                    for k, v in self.__plist_objects.items()])))
        self.__plist_objects = None # process complete


    def validate(self):
        if self.need_validate():
            rootObject = self.pbx_rootObject
            if rootObject is None:
                logger.warn(u'[XcodeProj] rootObject is None')

            try:
                rootObject.validate()
            except Exception as e:
                logger.warn(u'[XcodeProj] validation error:{ex}'.format(ex=e))
                raise

            isolate_objs = [obj for guid, obj in self.__objects.guid_items() \
                if len(obj.referrers()) == 0]
            if len(isolate_objs) > 0:
                logger.warn(u'[XcodeProj] isolate objects:\n\t{0}'\
                    .format(u'\n\t'.join([str(o) for o in isolate_objs])))

    def need_validate(self):
        for guid, obj in self.__objects.guid_items():
            return obj.isdirty()

    def save(self, tofile=None):
        buff = []
        self.write(buff)

        bakup_file = None
        if tofile is None:
            tofile = os.path.join(self.__project_file_path, self.__pbxfile)
            bakup_file = tofile + u'.bak'
            os.rename(tofile, bakup_file)

        try:
            with open(tofile, u'w') as fp:
                fp.writelines(buff)
        except Exception as e:
            logger.error(u'[XcodeProj] Can not write to file "{tofile}"; error:"{error}"'\
                .format(tofile=tofile, error=e))
            if not bakup_file is None and os.path.isfile(bakup_file):
                os.rename(bakup_file, tofile)
                logger.info(u'[XcodeProj] restore {pbxfile}'.format(pbxfile=self.__pbxfile))

    def write(self, buff, identstr=u''):
        plist_dic = {k[len(pbxconsts.PBX_ATTR_PREFIX):]:v \
            for k, v in self.__dict__.items() if func.hasprefix(k, pbxconsts.PBX_ATTR_PREFIX)}
        plist_dic[u'objects'] = self.__objects

        buff.append(u'// !$*UTF8*$!')
        buff.append(os.linesep)
        buff.append(u'{')
        buff.append(os.linesep)
        for k, v in sorted(plist_dic.items(), key=lambda o: o[0]):
            if k == u'objects':
                buff.append(u'\tobjects = {{{sep}'.format(sep=os.linesep))
                v.write(buff, u'\t')
                buff.append(u'\t}};{sep}'.format(sep=os.linesep))
            else:
                self._print_kv(buff, k, v, u'\t', singleline=False)
        buff.append(u'}')

    def get_object(self, guid):
        obj = self.__objects[guid]
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

    def __new_object(self, isa, guid=None):
        def __new_guid():
            import uuid
            from xcodeproj.pbxproj import pbxconsts

            for x in xrange(1,10):
                guid = uuid.uuid1().hex[0:pbxconsts.REFID_LEN].upper()
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
        try:
            return self.__new_object(isa)
        except Exception as e:
            logger.warn(e)
            return None

    def add_object(self, obj):
        assert isinstance(obj, baseobject.PBXBaseObject)
        self.__objects[obj.guid] = obj

    def remove_object(self, obj):
        guid = None
        if isinstance(obj, baseobject.PBXBaseObject):
            guid = obj.guid
        elif pbxhelper.is_valid_guid(obj):
            guid = obj

        if not guid is None:
            try:
                del self.__objects[guid]
            except Exception as e:
                pass
            
    def buildsettings(self, name):
        if os.getenv(u'PROJECT_FILE_PATH') == self.__project_file_path:
            return os.getenv(name)

        if name in [u'PROJECT_DIR', u'SRCROOT', u'SOURCE_ROOT']:
            return self.project_dir()
        elif name == u'PROJECT_NAME':
            return self.project_name()
        elif name == u'PROJECT_FILE_PATH':
            return self.__project_file_path
        return None

    def project_name(self):
        return os.path.splitext(os.path.basename(self.__project_file_path))[0]

    def project_dir(self):
        return os.path.dirname(self.__project_file_path)

    def main_group(self):
        return self.pbx_rootObject.pbx_mainGroup

    def get_target(self, name):
        return func.get_list_item(\
            func.take(lambda o:o.pbx_name == name, self.pbx_rootObject.pbx_targets), 0)




