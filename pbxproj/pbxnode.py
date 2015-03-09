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
from utils.template_function import *

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

SOURCE_TREE_ENMU = enum(
	group='<group>',
	absolute='<absolute>',
	SOURCE_ROOT='SOURCE_ROOT',
	DEVELOPER_DIR='DEVELOPER_DIR',
	BUILT_PRODUCTS_DIR='BUILT_PRODUCTS_DIR',
	SDKROOT='SDKROOT',
)

SOURCE_TREE_VALUES = {
	SOURCE_TREE_ENMU.group,
	SOURCE_TREE_ENMU.absolute,
	SOURCE_TREE_ENMU.SOURCE_ROOT,
	SOURCE_TREE_ENMU.DEVELOPER_DIR,
	SOURCE_TREE_ENMU.BUILT_PRODUCTS_DIR,
	SOURCE_TREE_ENMU.SDKROOT,
}


def isDict(obj):
	from collections import OrderedDict
	return type(obj) is dict or isinstance(obj, OrderedDict)


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


from pbxproj import *


# NOTE: internal vars using prefix: _al_
# Deperated
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

	def isValid(self):
		return re.match('[\dA-F]{24}', str(self.guid))


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
		elif confirmsTo == 'PBXGroup' and self.isa in {'PBXGroup', 'PBXVariantGroup'}:
			return True
		elif confirmsTo == 'PBXBuildPhase' and self.isa in {
													'PBXAppleScriptBuildPhase',
													'PBXCopyFilesBuildPhase',
													'PBXFrameworksBuildPhase',
													'PBXHeadersBuildPhase',
													'PBXResourcesBuildPhase',
													'PBXShellScriptBuildPhase',
													'PBXSourcesBuildPhase'
													}:
			return True
		else:
			return self.isa == confirmsTo

	def isValid(self, xcproj=None):
		if not self.isa == self.__class__.__name__:
			return False
		if not isinstance(self.guid, PBXRefID) or not self.guid.isValid():
			return False
		if xcproj and not str(self.guid) in xcproj.rootElement.objects:
			return False
		return True

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

	@staticmethod
	def isValidGuid(guid):
		return re.match('[\dA-F]{24}', guid)


class PBXBuildFile(PBXNode):
	def node(fileRef, guid=None):
		node = PBXBuildFile('PBXBuildFile', guid)
		node.fileRef = fileRef

	def __init__(self, isa='PBXBuildFile', guid=None):
		super(PBXBuildFile, self).__init__(isa, guid)
		self.settings = {}
		self.fileRef = None

	def _contentDict(self):
		dic = super(PBXBuildFile, self)._contentDict()
		if self.fileRef is not None:
			dic['fileRef'] = self.fileRef
		if isDict(self.settings) and len(self.settings) > 0:
			dic['settings'] = self.settings
		return dic

	def isValid(self, xcproj=None):
		if super(PBXBuildFile, self).isValid() and PBXRefID(self.fileRef).isValid():
			if xcproj:
				node = xcproj.nodeWithGuid(self.fileRef)
				if node and not node.isa in {'PBXFileReference', 'PBXVariantGroup', 'XCVersionGroup', 'PBXReferenceProxy'}:
					return False
		return True


class PBXContainerItemProxy(PBXNode):
	def node(self, guid=None):
		return PBXContainerItemProxy('PBXContainerItemProxy', guid)

	def __init__(self, isa='PBXContainerItemProxy', guid=None):
		super(PBXContainerItemProxy, self).__init__(isa, guid)
		self.containerPortal = None  # Project object
		self.proxyType = None
		self.remoteGlobalIDString = None
		self.remoteInfo = None

	def _contentDict(self):
		dic = super(PBXContainerItemProxy, self)._contentDict()
		myVars = {'containerPortal', 'proxyType', 'remoteGlobalIDString', 'remoteInfo'}
		dic1 = objectToDict(self, myVars)
		return dict(dic, **dic1)  # merge dict

	def isValid(self, xcproj=None):
		if super(PBXContainerItemProxy, self).isValid(xcproj):
			if self.containerPortal:
				if xcproj:
					node = xcproj.nodeWithGuid(self.containerPortal)
					valid = node and (node.isa == 'PBXProject' or node.isa == 'PBXFileReference' and node.fileType() == 'wrapper.pb-project')
					if not valid:
						return False
				elif not PBXRefID(self.containerPortal).isValid():
					return False

			if self.remoteGlobalIDString and not PBXRefID(self.remoteGlobalIDString).isValid():
				return False
		return True


#### PBXFileItems ###
class PBXFileReference(PBXNode):
	def __init__(self, isa='PBXFileReference', guid=None):
		super(PBXFileReference, self).__init__(isa, guid)
		self.fileEncoding = None
		self.explicitFileType = None
		self.lastKnownFileType = None
		self.path = None
		self.name = None
		self.sourceTree = SOURCE_TREE_ENMU.group
		self.includeInIndex = None
		self.xcLanguageSpecificationIdentifier = None
		self.lineEnding = None

	def _internalInit(self):
		super(PBXFileReference, self)._internalInit()
		if self.name is None and self.path is not None:
			self.name = os.path.basename(self.path)

	def isValid(self, xcproj=None):
		isValid = super(PBXFileReference, self).isValid(xcproj)
		return (
				isValid and self.path
				and self.sourceTree in SOURCE_TREE_VALUES
				and (self.explicitFileType or self.lastKnownFileType)
				)

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

	def fileType(self):
		return self.explicitFileType if self.explicitFileType else self.lastKnownFileType


class PBXGroup(PBXNode):
	"""docstring for PBXGroup"""
	def __init__(self, isa='PBXGroup', guid=None):
		super(PBXGroup, self).__init__(isa, guid)
		self.children = []
		self.name = None
		self.sourceTree = SOURCE_TREE_ENMU.group
		self.path = None

	def isValid(self, xcproj=None):
		if not super(PBXGroup, self).isValid(xcproj):
			return False
		if not self.sourceTree in SOURCE_TREE_VALUES:
			return False
		if not type(self.children) is list:
			return False
		for guid in self.children:
			if xcproj:
				childNode = xcproj.nodeWithGuid(str(guid))
				if not childNode \
					or not childNode.isa in {'PBXFileReference', 'PBXVariantGroup', 'XCVersionGroup', 'PBXReferenceProxy', 'PBXGroup'}:
					return False
			elif not PBXRefID(guid).isValid():
				return False
		return True

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
		self.name = os.path.basename(self.path) if self.name is None and self.path is not None else self.name
		if self.name is not None and self.name != self.path:
			dic['name'] = self.name
		return dict(objectToDict(self, {'sourceTree', 'path'}), **dic)


class PBXVariantGroup(PBXGroup):
	"""docstring for PBXVariantGroup"""
	def __init__(self, isa='PBXVariantGroup', guid=None):
		super(PBXVariantGroup, self).__init__(isa, guid)

	def node(self, children=(), guid=None):
		node = PBXVariantGroup('PBXVariantGroup', guid)
		node.children = list(children)
		return node


class XCVersionGroup(PBXGroup):
	"""docstring for XCVersionGroup"""
	def __init__(self, isa='XCVersionGroup', guid=None):
		super(XCVersionGroup, self).__init__(isa, guid)
		self.currentVersion = None
		self.versionGroupType = None

	def _contentDict(self):
		dic = super(XCVersionGroup, self)._contentDict()
		return dict(objectToDict(self, {'currentVersion', 'versionGroupType'}), **dic)

	def isValid(self, xcproj=None):
		if not super(XCVersionGroup, self).isValid(xcproj) or not PBXRefID(self.currentVersion).isValid():
			return False
		elif xcproj and not self.currentVersion in xcproj.rootElement.objects:
			return False
		elif not PBXRefID(self.currentVersion).isValid():
			return False
		return True


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

	def isValid(self, xcproj=None):
		if not super(PBXBuildPhase, self).isValid():
			return False
		if not type(self.files) is list:
			return False
		for guid in self.files:
			if xcproj:
				node = xcproj.nodeWithGuid(guid)
				if not node or not node.isaConfirmsTo('PBXBuildFile'):
					return False
			elif not PBXRefID(guid).isValid():
				return False
		return True


class PBXAppleScriptBuildPhase(PBXBuildPhase):
	"""docstring for ClassName"""
	def node(self, files=(), guid=None):
		return super(PBXAppleScriptBuildPhase, self).node('PBXAppleScriptBuildPhase', files, guid)


class PBXCopyFilesBuildPhase(PBXBuildPhase):
	"""docstring for PBXCopyFilesBuildPhase"""
	def __init__(self, isa='PBXAppleScriptBuildPhase', guid=None):
		super(PBXCopyFilesBuildPhase, self).__init__(isa, guid)
		self.dstPath = None
		self.dstSubfolderSpec = None

	def node(self, files=(), guid=None):
		return super(PBXCopyFilesBuildPhase, self).node('PBXCopyFilesBuildPhase', files, guid)

	def _contentDict(self):
		dic = super(PBXCopyFilesBuildPhase, self)._contentDict()
		return dict(objectToDict(self, {'dstPath', 'dstSubfolderSpec'}), **dic)


class PBXFrameworksBuildPhase(PBXBuildPhase):
	"""docstring for PBXFrameworksBuildPhase"""
	def __init__(self, isa='PBXFrameworksBuildPhase', guid=None):
		super(PBXFrameworksBuildPhase, self).__init__(isa, guid)
		self._al_displayName = 'Frameworks'

	def node(self, files=(), guid=None):
		return super(PBXFrameworksBuildPhase, self).node('PBXFrameworksBuildPhase', files, guid)


class PBXHeadersBuildPhase(PBXBuildPhase):
	"""docstring for PBXHeadersBuildPhase"""
	def __init__(self, isa='PBXHeadersBuildPhase', guid=None):
		super(PBXHeadersBuildPhase, self).__init__(isa, guid)

	def node(self, files=(), guid=None):
		return super(PBXHeadersBuildPhase, self).node('PBXHeadersBuildPhase', files, guid)


class PBXResourcesBuildPhase(PBXBuildPhase):
	"""docstring for PBXResourcesBuildPhase"""
	def __init__(self, isa='PBXResourcesBuildPhase', guid=None):
		super(PBXResourcesBuildPhase, self).__init__(isa, guid)
		self._al_displayName = 'Resources'

	def node(self, files=(), guid=None):
		return super(PBXResourcesBuildPhase, self).node('PBXResourcesBuildPhase', files, guid)


class PBXShellScriptBuildPhase(PBXBuildPhase):
	"""docstring for PBXShellScriptBuildPhase"""
	def __init__(self, isa='PBXShellScriptBuildPhase', guid=None):
		super(PBXShellScriptBuildPhase, self).__init__(isa, guid)
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
	def __init__(self, isa='PBXSourcesBuildPhase', guid=None):
		super(PBXSourcesBuildPhase, self).__init__(isa, guid)
		self._al_displayName = 'Sources'

	def node(self, files=(), guid=None):
		return super(PBXSourcesBuildPhase, self).node('PBXSourcesBuildPhase', files, guid)


### PBXTarget ###
class PBXAggregateTarget(PBXNode):
	"""docstring for PBXAggregateTarget"""
	def __init__(self, isa='PBXAggregateTarget', guid=None):
		super(PBXAggregateTarget, self).__init__(isa, guid)
		self.buildConfigurationList = None
		self.buildPhases = []
		self.dependencies = []
		self.name = None
		self.productName = None

	def isValid(self, xcproj=None):
		if not super(PBXAggregateTarget, self).isValid():
			return False
		if self.buildConfigurationList and not PBXRefID(self.buildConfigurationList).isValid():
			return False
		if not type(self.buildPhases) is list or not type(self.dependencies) is list:
			return False
		if xcproj:
			for guid in self.buildPhases:
				node = xcproj.nodeWithGuid(guid)
				if not node or not node.isaConfirmsTo('PBXBuildPhase'):
					return False
			for guid in self.dependencies:
				node = xcproj.nodeWithGuid(guid)
				if not node or node.isaConfirmsTo('PBXTargetDependency'):
					return False
		elif len(filter(lambda n: not PBXRefID(n).isValid(), self.buildPhases.extend(self.buildConfigurationList))) > 0:
			return False
		return True

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
	def __init__(self, isa='PBXLegacyTarget', guid=None):
		super(PBXLegacyTarget, self).__init__(isa, guid)


class PBXNativeTarget(PBXNode):
	"""docstring for PBXNativeTarget"""
	def __init__(self, isa='PBXNativeTarget', guid=None):
		super(PBXNativeTarget, self).__init__(isa, guid)
		self.buildConfigurationList = None
		self.buildPhases = []
		self.dependencies = []
		self.name = None
		self.productInstallPath = None
		self.productName = None
		self.productReference = None
		self.productType = None
		self.buildRules = []

	def isValid(self, xcproj=None):
		if not super(PBXNativeTarget, self).isValid():
			return False
		if self.buildConfigurationList:
			if xcproj:
				node = xcproj.nodeWithGuid(self.buildConfigurationList)
				if not node or not node.isaConfirmsTo('XCConfigurationList'):
					return False
			elif not PBXRefID(self.buildConfigurationList).isValid():
				return False
		if self.productReference:
			if xcproj:
				node = xcproj.nodeWithGuid(self.productReference)
				if not node or not (node.isaConfirmsTo('PBXFileReference') and node.fileType() in {'wrapper.application', 'wrapper.cfbundle', 'wrapper.app-extension'}):
					return False
			elif not PBXRefID(self.productReference).isValid():
				return False
		if not type(self.buildPhases) is list or not type(self.dependencies) is list:
			return False
		if xcproj:
			for guid in self.buildPhases:
				node = xcproj.nodeWithGuid(guid)
				if not node or not node.isaConfirmsTo('PBXBuildPhase'):
					return False
			for guid in self.dependencies:
				node = xcproj.nodeWithGuid(guid)
				if not node or not node.isaConfirmsTo('PBXTargetDependency'):
					return False
		elif len(filter(lambda n: not PBXRefID(n).isValid(), self.buildPhases.extend(self.buildConfigurationList))) > 0:
			return False
		return True

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
	def __init__(self, isa='PBXProject', guid=None):
		super(PBXProject, self).__init__(isa, guid)
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

	def isValid(self, xcproj=None):
		if not super(PBXProject, self).isValid():
			return False
		if not self.mainGroup or not PBXRefID(self.mainGroup).isValid():
			return False
		if self.productRefGroup and not PBXRefID(self.productRefGroup).isValid():
			return False
		if self.buildConfigurationList and not PBXRefID(self.buildConfigurationList).isValid():
			return False

		if not type(self.targets) is list:
			return False
		for guid in self.targets:
			node = xcproj.nodeWithGuid(guid)
			if not node or not node.isaConfirmsTo('PBXTarget'):
				return False

		if isDict(self.attributes):
			targetAttrs = self.attributes['TargetAttributes']
			if isDict(targetAttrs):
				for k, v in targetAttrs.items():
					if k not in self.targets:
						return False
					if isDict(v) and 'TestTargetID' in v:
						if v['TestTargetID'] not in self.targets:
							return False
		if type(self.projectReferences) is list:
			for item in filter(lambda item: isDict(item), self.projectReferences):
				for k, v in item.items():
					if xcproj:
						if k == 'ProductGroup':
							node = xcproj.nodeWithGuid(v)
							if not node or not node.isaConfirmsTo('PBXGroup'):
								return False
						elif k == 'ProjectRef':
							node = xcproj.nodeWithGuid(v)
							if not node or not (node.isaConfirmsTo('PBXFileReference') and node.fileType() == 'wrapper.pb-project'):
								return False

					elif k in {'ProductGroup', 'ProjectRef'}:
						if not PBXRefID(v).isValid():
							return False
		return True

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
	def __init__(self, isa='PBXTargetDependency', guid=None):
		super(PBXTargetDependency, self).__init__(isa, guid)
		self.target = None
		self.targetProxy = None
		self.name = None

	def isValid(self, xcproj=None):
		if not super(PBXTargetDependency, self).isValid(xcproj):
			return False
		if self.targetProxy:
			if xcproj:
				node = xcproj.nodeWithGuid(self.targetProxy)
				if not node or not node.isaConfirmsTo('PBXContainerItemProxy'):
					return False
			elif not PBXRefID(self.targetProxy).isValid():
				return False
		if self.target:
			if xcproj:
				node = xcproj.nodeWithGuid(self.target)
				if not node or not node.isaConfirmsTo('PBXTarget'):
					return False
			elif not PBXRefID(self.target).isValid():
				return False
		return True

	def _contentDict(self):
		dic = super(PBXTargetDependency, self)._contentDict()
		return dict(objectToDict(self, {
			'target',
			'targetProxy',
			'name'
			}), **dic)


class XCBuildConfiguration(PBXNode):
	"""docstring for XCBuildConfiguration"""
	def __init__(self, isa='XCBuildConfiguration', guid=None):
		super(XCBuildConfiguration, self).__init__(isa, guid)
		self.baseConfigurationReference = None
		self.buildSettings = {}
		self.name = None

	def isValid(self, xcproj=None):
		if not super(XCBuildConfiguration, self).isValid(xcproj):
			return False

		if self.baseConfigurationReference:
			if xcproj:
				node = xcproj.nodeWithGuid(self.baseConfigurationReference)
				if not node or not (node.isaConfirmsTo('PBXFileReference') and node.fileType() == 'text.xcconfig'):
					return False
			elif not PBXRefID(self.baseConfigurationReference).isValid():
				return False
		return isDict(self.buildSettings) if self.buildSettings else True

	def _contentDict(self):
		dic = super(XCBuildConfiguration, self)._contentDict()
		resultDict = dict(objectToDict(self, {
			'baseConfigurationReference',
			'buildSettings',
			'name'
			}), **dic)
		if 'buildSettings' in resultDict and isDict(resultDict['buildSettings']):
			from collections import OrderedDict
			originalDict = resultDict['buildSettings']
			settingsDict = OrderedDict((k, originalDict[k]) for k in sorted(originalDict.keys()))
			resultDict['buildSettings'] = settingsDict
		return resultDict


class XCConfigurationList(PBXNode):
	"""docstring for XCConfigurationList"""
	def __init__(self, isa='XCConfigurationList', guid=None):
		super(XCConfigurationList, self).__init__(isa, guid)
		self.buildConfigurations = []
		self.defaultConfigurationIsVisible = None
		self.defaultConfigurationName = None

	def isValid(self, xcproj=None):
		if not super(XCConfigurationList, self).isValid(xcproj):
			return False

		if type(self.buildConfigurations) is list:
			for guid in self.buildConfigurations:
				if xcproj:
					node = xcproj.nodeWithGuid(guid)
					if not node or not node.isaConfirmsTo('XCBuildConfiguration'):
						return False
				elif not PBXRefID(guid).isValid():
					return False
		return True

	def _contentDict(self):
		dic = super(XCConfigurationList, self)._contentDict()
		return dict(objectToDict(self, {
			'buildConfigurations',
			'defaultConfigurationIsVisible',
			'defaultConfigurationName'
			}), **dic)


class PBXReferenceProxy(PBXNode):
	"""docstring for PBXReferenceProxy"""
	def __init__(self, isa='PBXReferenceProxy', guid=None):
		super(PBXReferenceProxy, self).__init__(isa, guid)
		self.fileType = None
		self.path = None
		self.remoteRef = None
		self.sourceTree = None
		self.name = None

	def isValid(self, xcproj=None):
		if not super(PBXReferenceProxy, self).isValid():
			return False
		if not self.path or not self.sourceTree in SOURCE_TREE_VALUES:
			return False
		if self.remoteRef:
			if xcproj:
				node = xcproj.nodeWithGuid(self.remoteRef)
				if not node or not node.isaConfirmsTo('PBXContainerItemProxy'):
					return False

			elif not PBXRefID(self.remoteRef).isValid():
				return False
		return True

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

	def isValid(self, xcproj=None):
		return isDict(self.objects) and self.rootObject and self.rootObject in self.objects and isDict(self.objects)

	def toDict(self):
		return objectToDict(self, {
			'archiveVersion',
			'classes',
			'objectVersion',
			'objects',
			'rootObject'
			})

##################################################################################

if __name__ == '__main__':
	node = PBXVariantGroup().node()
	print node.__class__.__name__
	print node.isa
	print 'equal' if node.__class__.__name__ == node.isa else 'No'
