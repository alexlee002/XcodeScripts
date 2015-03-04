#!/usr/bin/python
#encoding:utf-8
#Filename: pbxnode.py

import os
import sys
#import subprocess

mymoduleRoot = os.path.join(os.path.dirname(__file__), "..")
if not mymoduleRoot in sys.path:
	sys.path.append(mymoduleRoot)

import utils
#from utils.logger import Logger

FILETYPE_BY_EXT = {
	'.h':			'sourcecode.c.h',
	'.m':			'sourcecode.c.objc',
	'.pch': 		'sourcecode.c.h',
	'.swift': 		'sourcecode.swift',
	'.c':			'sourcecode.c.c',
	'.mm':			'sourcecode.cpp.objcpp',
	'.hpp':			'sourcecode.cpp.h',
	'.cpp':			'sourcecode.cpp.cpp',
	'.cc':			'sourcecode.cpp.cpp',
	'.png':			'image.png',
	'.jpeg':		'image.jpeg',
	'.jpg':			'image.jpeg',
	'.mp3':			'audio.mp3',
	'.wav':			'audio.wav',
	'.a':			'archive.ar',
	'.app':			'wrapper.application',
	'.bundle':		'wrapper.plug-in',
	'.framework':	'wrapper.framework',
	'.mdimporter': 	'wrapper.cfbundle',
	'.octest': 		'wrapper.cfbundle',
	'.xcdatamodel': 'wrapper.xcdatamodel',
	'.xcodeproj': 	'wrapper.pb-project',
	'.xctest': 		'wrapper.cfbundle',
	'.markdown': 	'text',
	'.fnt':			'text',
	'.txt':			'text',
	'.plist': 		'text.plist.xml',
	'.sh': 			'text.script.sh',
	'.xcconfig': 	'text.xcconfig',
	'.strings':		'text.plist.strings',
	'.entitlements': 'text.xml',
	'.storyboard':	'file.storyboard',
	'.xib': 		'file.xib',
	'.xcassets': 	'folder.assetcatalog',
	'.dylib':		'compiled.mach-o.dylib',
}

HEADER_FILE_EXTS = {'.h', '.pch', '.hh', '.hpp', '.ipp', '.tpp'}


# properties is a set
def objectToDict(obj, properties={}, allowNoneValue=False):
	from collections import OrderedDict
	objVars = vars(obj)
	dic = {}
	if type(properties) is set:
		properties = sorted([p for p in properties])
		for varName, varVal in OrderedDict((var, objVars[var]) for var in properties if var in objVars).items():
			if varVal is not None or allowNoneValue:
				dic[varName] = varVal
	elif type(properties) is dict:
		for varName in sorted([k for k in properties.keys()]):
			dftVal = properties[varName]
			if varName in objVars and objVars[varName] is not None:
				dic[varName] = objVars[varName]
			else:
				dic[varName] = dftVal
	elif type(properties) is OrderedDict:
		for varName, dftVal in properties.items():
			if varName in objVars and objVars[varName] is not None:
				dic[varName] = objVars[varName]
			else:
				dic[varName] = dftVal
	return dic


# NOTE: internal vars using prefix: _al_
class PBXRefID(object):
	def __init__(self, guid=None):
		super(PBXRefID, self).__init__()
		self.guid = guid

	def __str__(self):
		self.guid = self.guid if self.guid else utils.functions.genRandomString(24).upper()
		return str(self.guid)

	def __repr__(self):
		self.guid = self.guid if self.guid else utils.functions.genRandomString(24).upper()
		return repr(self.guid)


class PBXBaseObject(object):
	def toDict(self):
		pass


class PBXNode(PBXBaseObject):
	def __init__(self, isa, guid=None):
		super(PBXNode, self).__init__()
		self.isa = isa
		self.guid = PBXRefID(guid)

	def _internalInit(self):
		pass

	def node(self, isa, guid=None):
		return PBXNode(isa, guid)

	def toDict(self):
		return {self.guid: self._contentDict()}

	def _contentDict(self):
		return {'isa': self.isa}

	def __str__(self):
		return str(self.toDict())

	def __repr__(self):
		return repr(self.toDict())

	def isaConfirmsTo(self, confirmsTo):
		if confirmsTo == 'PBXTarget' and self.isa in {'PBXNativeTarget', 'PBXAggregateTarget', 'PBXLegacyTarget'}:
			return True
		if confirmsTo == 'PBXBuildPhase' and self.isa in {
													'PBXAppleScriptBuildPhase',
													'PBXCopyFilesBuildPhase',
													'PBXFrameworksBuildPhase',
													'PBXHeadersBuildPhase',
													'PBXResourcesBuildPhase',
													'PBXShellScriptBuildPhase',
													'PBXSourcesBuildPhase'
													}:
			return True
		return self.isa == confirmsTo

	@staticmethod
	def nodeFromDict(dic={}, guid=None):
		isa = dic['isa'] if 'isa' in dic else None
		if isa:
			try:
				node = getattr(sys.modules[__name__], isa)(isa, guid)
			except Exception, e:
				utils.logger.Logger().error('PBXNode: "%s" is not supported yet: %s' % (isa, e))
				return None
			selfVars = vars(node).keys()
			for k, v in dic.items():
				if k in selfVars:
					setattr(node, k, v)
				else:
					utils.logger.Logger().warn('property:"%s" is not supported by PBXNode:%s yet' % (k, type(node)))
			node._internalInit()
			return node
		return None


class PBXBuildFile(PBXNode):
	def node(fileRef, guid=None):
		node = PBXBuildFile('PBXBuildFile', guid)
		node.fileRef = fileRef

	def __init__(self, isa=None, guid=None):
		super(PBXBuildFile, self).__init__('PBXBuildFile', guid)
		self.settings = {}
		self.fileRef = None

	def _contentDict(self):
		dic = super(PBXBuildFile, self)._contentDict()
		if self.fileRef is not None:
			dic['fileRef'] = self.fileRef
		if type(self.settings) is dict and len(self.settings) > 0:
			dic['settings'] = self.settings
		return dic


class PBXContainerItemProxy(PBXNode):
	def node(self, guid=None):
		return PBXContainerItemProxy('PBXContainerItemProxy', guid)

	def __init__(self, isa=None, guid=None):
		super(PBXContainerItemProxy, self).__init__('PBXContainerItemProxy', guid)
		self.containerPortal = None  # Project object
		self.proxyType = None
		self.remoteGlobalIDString = None
		self.remoteInfo = None

	def _contentDict(self):
		dic = super(PBXContainerItemProxy, self)._contentDict()
		myVars = {'containerPortal', 'proxyType', 'remoteGlobalIDString', 'remoteInfo'}
		dic1 = objectToDict(self, myVars)
		return dict(dic, **dic1)  # merge dict


#### PBXFileItems ###
class PBXFileReference(PBXNode):
	def __init__(self, isa=None, guid=None):
		super(PBXFileReference, self).__init__('PBXFileReference', guid)
		self.fileEncoding = None
		self.explicitFileType = None
		self.lastKnownFileType = None
		self.path = None
		self.name = None
		self.sourceTree = '<group>'
		self.includeInIndex = None
		self.xcLanguageSpecificationIdentifier = None
		self.lineEnding = None

	def _internalInit(self):
		super(PBXFileReference, self)._internalInit()
		if self.name is None and self.path is not None:
			self.name = os.path.basename(self.path)

	def node(self, path, guid=None):
		node = PBXFileReference('PBXFileReference', guid)
		self.path = path
		self.name = os.path.basename(path)
		ext = os.path.splitext(path)[1].lower()
		self.lastKnownFileType = FILETYPE_BY_EXT[ext] if ext in FILETYPE_BY_EXT else None
		#self.explicitFileType = FILETYPE_BY_EXT[ext] if ext in FILETYPE_BY_EXT else None
		return node

	def _contentDict(self):
		dic = super(PBXFileReference, self)._contentDict()
		myVars = {
					'fileEncoding',
					'path',
					'sourceTree',
					'includeInIndex',
					'xcLanguageSpecificationIdentifier',
					'lineEnding',
					}
		dic = dict(objectToDict(self, myVars), **dic)
		if self.explicitFileType is not None:
			dic['explicitFileType'] = self.explicitFileType
		elif self.lastKnownFileType is not None:
			dic['lastKnownFileType'] = self.lastKnownFileType
		if self.name is not None and self.name != self.path:
			dic['name'] = self.name
		return dic


class PBXGroup(PBXNode):
	"""docstring for PBXGroup"""
	def __init__(self, isa=None, guid=None):
		super(PBXGroup, self).__init__('PBXGroup', guid)
		self.children = []
		self.name = None
		self.sourceTree = '<group>'
		self.path = None

	def node(self, children=(), guid=None):
		node = PBXGroup('PBXGroup', guid)
		node.children = list(children)
		return node

	def _internalInit(self):
		super(PBXGroup, self)._internalInit()
		if self.name is None and self.path is not None:
			self.name = os.path.basename(self.path)

	def _contentDict(self):
		dic = super(PBXGroup, self)._contentDict()
		dic['children'] = self.children if self.children is not None else []
		if self.name is not None and self.name != self.path:
			dic['name'] = self.name
		return dict(objectToDict(self, {'sourceTree', 'path'}), **dic)


class PBXVariantGroup(PBXGroup):
	"""docstring for PBXVariantGroup"""
	def __init__(self, isa=None, guid=None):
		super(PBXVariantGroup, self).__init__('PBXVariantGroup', guid)

	def node(self, children=(), guid=None):
		node = PBXVariantGroup('PBXVariantGroup', guid)
		node.children = list(children)
		return node


class XCVersionGroup(PBXGroup):
	"""docstring for XCVersionGroup"""
	def __init__(self, isa=None, guid=None):
		super(XCVersionGroup, self).__init__('XCVersionGroup', guid)
		self.currentVersion = None
		self.versionGroupType = None

	def _contentDict(self):
		dic = super(XCVersionGroup, self)._contentDict()
		return dict(objectToDict(self, {'currentVersion', 'versionGroupType'}), **dic)


### PBXBuildPhases ###
class PBXBuildPhase(PBXNode):
	"""base class of build phase node"""
	def __init__(self, isa, guid=None):
		super(PBXBuildPhase, self).__init__(isa, guid)
		self.files = []
		self.buildActionMask = 2147483647
		self.runOnlyForDeploymentPostprocessing = 0
		self.name = None
		self._al_displayName = None

	def node(self, isa, files=(), guid=None):
		node = PBXBuildPhase(isa, guid)
		node.files = list(files)
		return node

	def _contentDict(self):
		dic = super(PBXBuildPhase, self)._contentDict()
		myDic = objectToDict(self, {'files', 'buildActionMask', 'runOnlyForDeploymentPostprocessing'})
		if self.name is not None:
			myDic['name'] = self.name
		return dict(myDic, **dic)


class PBXAppleScriptBuildPhase(PBXBuildPhase):
	"""docstring for ClassName"""
	def node(self, files=(), guid=None):
		return super(PBXAppleScriptBuildPhase, self).node('PBXAppleScriptBuildPhase', files, guid)


class PBXCopyFilesBuildPhase(PBXBuildPhase):
	"""docstring for PBXCopyFilesBuildPhase"""
	def __init__(self, isa=None, guid=None):
		super(PBXCopyFilesBuildPhase, self).__init__('PBXCopyFilesBuildPhase', guid)
		self.dstPath = None
		self.dstSubfolderSpec = None

	def node(self, files=(), guid=None):
		return super(PBXCopyFilesBuildPhase, self).node('PBXCopyFilesBuildPhase', files, guid)

	def _contentDict(self):
		dic = super(PBXCopyFilesBuildPhase, self)._contentDict()
		return dict(objectToDict(self, {'dstPath', 'dstSubfolderSpec'}), **dic)


class PBXFrameworksBuildPhase(PBXBuildPhase):
	"""docstring for PBXFrameworksBuildPhase"""
	def __init__(self, isa=None, guid=None):
		super(PBXFrameworksBuildPhase, self).__init__('PBXFrameworksBuildPhase', guid)
		self._al_displayName = 'Frameworks'

	def node(self, files=(), guid=None):
		return super(PBXFrameworksBuildPhase, self).node('PBXFrameworksBuildPhase', files, guid)


class PBXHeadersBuildPhase(PBXBuildPhase):
	"""docstring for PBXHeadersBuildPhase"""
	def __init__(self, isa=None, guid=None):
		super(PBXHeadersBuildPhase, self).__init__('PBXHeadersBuildPhase', guid)

	def node(self, files=(), guid=None):
		return super(PBXHeadersBuildPhase, self).node('PBXHeadersBuildPhase', files, guid)


class PBXResourcesBuildPhase(PBXBuildPhase):
	"""docstring for PBXResourcesBuildPhase"""
	def __init__(self, isa=None, guid=None):
		super(PBXResourcesBuildPhase, self).__init__('PBXResourcesBuildPhase', guid)
		self._al_displayName = 'Resources'

	def node(self, files=(), guid=None):
		return super(PBXResourcesBuildPhase, self).node('PBXResourcesBuildPhase', files, guid)


class PBXShellScriptBuildPhase(PBXBuildPhase):
	"""docstring for PBXShellScriptBuildPhase"""
	def __init__(self, isa=None, guid=None):
		super(PBXShellScriptBuildPhase, self).__init__('PBXShellScriptBuildPhase', guid)
		self.inputPaths = []
		self.outputPaths = []
		self.shellPath = None
		self.shellScript = None

	def node(self, files=(), guid=None):
		return super(PBXShellScriptBuildPhase, self).node('PBXShellScriptBuildPhase', files, guid)

	def _contentDict(self):
		dic = super(PBXShellScriptBuildPhase, self)._contentDict()
		return dict(objectToDict(self, {'inputPaths', 'outputPaths', 'shellPath', 'shellScript'}), **dic)


class PBXSourcesBuildPhase(PBXBuildPhase):
	"""docstring for PBXSourcesBuildPhase"""
	def __init__(self, isa=None, guid=None):
		super(PBXSourcesBuildPhase, self).__init__('PBXSourcesBuildPhase', guid)
		self._al_displayName = 'Sources'

	def node(self, files=(), guid=None):
		return super(PBXSourcesBuildPhase, self).node('PBXSourcesBuildPhase', files, guid)


### PBXTarget ###
class PBXAggregateTarget(PBXNode):
	"""docstring for PBXAggregateTarget"""
	def __init__(self, isa=None, guid=None):
		super(PBXAggregateTarget, self).__init__('PBXAggregateTarget', guid)
		self.buildConfigurationList = None
		self.buildPhases = []
		self.dependencies = []
		self.name = None
		self.productName = None

	def _contentDict(self):
		dic = super(PBXAggregateTarget, self)._contentDict()
		return dict(objectToDict(self, {
			'buildConfigurationList',
			'buildPhases',
			'dependencies',
			'name',
			'productName'
			}), **dic)


class PBXLegacyTarget(PBXNode):
	"""docstring for PBXLegacyTarget"""
	def __init__(self, isa=None, guid=None):
		super(PBXLegacyTarget, self).__init__('PBXLegacyTarget', guid)


class PBXNativeTarget(PBXNode):
	"""docstring for PBXNativeTarget"""
	def __init__(self, isa=None, guid=None):
		super(PBXNativeTarget, self).__init__('PBXNativeTarget', guid)
		self.buildConfigurationList = None
		self.buildPhases = []
		self.dependencies = []
		self.name = None
		self.productInstallPath = None
		self.productName = None
		self.productReference = None
		self.productType = None
		self.buildRules = []

	def _contentDict(self):
		dic = super(PBXNativeTarget, self)._contentDict()
		return dict(objectToDict(self, {
			'buildConfigurationList',
			'buildPhases',
			'dependencies',
			'name',
			'productInstallPath',
			'productName',
			'productReference',
			'productType',
			'buildRules'
			}), **dic)


class PBXProject(PBXNode):
	"""docstring for PBXProject"""
	def __init__(self, isa=None, guid=None):
		super(PBXProject, self).__init__('PBXProject', guid)
		self.buildConfigurationList = None
		self.compatibilityVersion = None
		self.developmentRegion = None
		self.hasScannedForEncodings = None
		self.knownRegions = []
		self.mainGroup = None
		self.productRefGroup = None
		self.projectDirPath = None
		self.projectReferences = None
		self.projectRoot = None
		self.targets = []
		self.attributes = {}

	def _contentDict(self):
		dic = super(PBXProject, self)._contentDict()
		return dict(objectToDict(self, {
			'buildConfigurationList',
			'compatibilityVersion',
			'developmentRegion',
			'hasScannedForEncodings',
			'knownRegions',
			'mainGroup',
			'productRefGroup',
			'projectDirPath',
			'projectReferences',
			'projectRoot',
			'targets',
			'attributes'
			}), **dic)


class PBXTargetDependency(PBXNode):
	"""docstring for PBXTargetDependency"""
	def __init__(self, isa=None, guid=None):
		super(PBXTargetDependency, self).__init__('PBXTargetDependency', guid)
		self.target = None
		self.targetProxy = None
		self.name = None

	def _contentDict(self):
		dic = super(PBXTargetDependency, self)._contentDict()
		return dict(objectToDict(self, {
			'target',
			'targetProxy',
			'name'
			}), **dic)


class XCBuildConfiguration(PBXNode):
	"""docstring for XCBuildConfiguration"""
	def __init__(self, isa=None, guid=None):
		super(XCBuildConfiguration, self).__init__('XCBuildConfiguration', guid)
		self.baseConfigurationReference = None
		self.buildSettings = {}
		self.name = None

	def _contentDict(self):
		dic = super(XCBuildConfiguration, self)._contentDict()
		resultDict = dict(objectToDict(self, {
			'baseConfigurationReference',
			'buildSettings',
			'name'
			}), **dic)
		if 'buildSettings' in resultDict and type(resultDict['buildSettings']) is dict:
			from collections import OrderedDict
			originalDict = resultDict['buildSettings']
			settingsDict = OrderedDict((k, originalDict[k]) for k in sorted(originalDict.keys()))
			resultDict['buildSettings'] = settingsDict
		return resultDict


class XCConfigurationList(PBXNode):
	"""docstring for XCConfigurationList"""
	def __init__(self, isa=None, guid=None):
		super(XCConfigurationList, self).__init__('XCConfigurationList', guid)
		self.buildConfigurations = []
		self.defaultConfigurationIsVisible = None
		self.defaultConfigurationName = None

	def _contentDict(self):
		dic = super(XCConfigurationList, self)._contentDict()
		return dict(objectToDict(self, {
			'buildConfigurations',
			'defaultConfigurationIsVisible',
			'defaultConfigurationName'
			}), **dic)


class PBXReferenceProxy(PBXNode):
	"""docstring for PBXReferenceProxy"""
	def __init__(self, isa=None, guid=None):
		super(PBXReferenceProxy, self).__init__('PBXReferenceProxy', guid)
		self.fileType = None
		self.path = None
		self.remoteRef = None
		self.sourceTree = None
		self.name = None

	def _internalInit(self):
		super(PBXReferenceProxy, self)._internalInit()
		if self.name is None and self.path is not None:
			self.name = os.path.basename(self.path)

	def _contentDict(self):
		dic = super(PBXReferenceProxy, self)._contentDict()
		return dict(objectToDict(self, {
			'fileType',
			'path',
			'name',
			'sourceTree',
			'remoteRef'
			}), **dic)


class RootElement(PBXBaseObject):
	"""docstring for RootElement"""
	def __init__(self):
		super(RootElement, self).__init__()
		self.archiveVersion = 1
		self.classes = []
		self.objectVersion = None
		self.objects = {}
		self.rootObject = None

	def toDict(self):
		return objectToDict(self, {
			'archiveVersion',
			'classes',
			'objectVersion',
			'objects',
			'rootObject'
			})
