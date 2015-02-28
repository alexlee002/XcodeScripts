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


# NOTE: internal vars using prefix: _al_
class PBXNode(object):
	def __init__(self, isa, guid=None):
		super(PBXNode, self).__init__()
		self._al_commentName = None  # displayed in comments
		self._al_rawDict = None  # original data from pbxproj
		self.isa = isa
		self.guid = guid
		if self.guid is None:
			self.guid = self._genGuid()

	def internalInit(self):
		pass

	def _genGuid(self):
		import uuid
		import md5
		guid = md5.new()
		guid.update(str(uuid.uuid1))
		return str(guid.hexdigest()).upper()

	@staticmethod
	def nodeFromDict(dic={}, guid=None):
		isa = dic['isa'] if 'isa' in dic else None
		if isa:
			try:
				node = getattr(sys.modules[__name__], isa)(isa, guid)
			except Exception, e:
				utils.logger.Logger().error('PBXNode: "%s" not supported: %s' % (isa, e))
				return

			node._al_rawDict = dic
			selfVars = [var for var in vars(node).keys() if not utils.functions.stringHasPrefix(var, '_al_')]
			for k, v in dic.items():
				if k in selfVars:
					setattr(node, k, v)
				else:
					utils.logger.Logger().warn('property:"%s" not in PBXNode:%s' % (k, type(node)))
			node.internalInit()
			return node
		return None

	def node(self, isa, guid=None):
		return PBXNode(isa, guid)


class PBXBuildFile(PBXNode):
	"""example: 43485E961A91CAA800BAB057 /* main.m in Sources */ = {isa = PBXBuildFile; fileRef = 43485E951A91CAA800BAB057 /* main.m */; };"""

	def node(fileRef, guid=None):
		node = PBXBuildFile('PBXBuildFile', guid)
		node.fileRef = fileRef

	def __init__(self, isa=None, guid=None):
		super(PBXBuildFile, self).__init__('PBXBuildFile', guid)
		self.settings = {}
		self.fileRef = None


class PBXContainerItemProxy(PBXNode):
	def node(self, guid=None):
		return PBXContainerItemProxy('PBXContainerItemProxy', guid)

	def __init__(self, isa=None, guid=None):
		super(PBXContainerItemProxy, self).__init__('PBXContainerItemProxy', guid)
		self.containerPortal = None  # Project object
		self.proxyType = None
		self.remoteGlobalIDString = None
		self.remoteInfo = None


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
		self._al_buildPhase = None

	def internalInit(self):
		super(PBXFileReference, self).internalInit()
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

	def internalInit(self):
		super(PBXGroup, self).internalInit()
		if self.name is None and self.path is not None:
			self.name = os.path.basename(self.path)


class PBXVariantGroup(PBXNode):
	"""docstring for PBXVariantGroup"""
	def __init__(self, isa=None, guid=None):
		super(PBXVariantGroup, self).__init__('PBXVariantGroup', guid)
		self.children = []
		self.name = None
		self.sourceTree = '<group>'

	def node(self, children=(), guid=None):
		node = PBXVariantGroup('PBXVariantGroup', guid)
		node.children = list(children)
		return node


class XCVersionGroup(PBXNode):
	"""docstring for XCVersionGroup"""
	def __init__(self, isa=None, guid=None):
		super(XCVersionGroup, self).__init__('XCVersionGroup', guid)
		self.children = []
		self.currentVersion = None
		self.path = None
		self.sourceTree = '<group>'
		self.versionGroupType = None
		self.name = None

	def internalInit(self):
		super(XCVersionGroup, self).internalInit()
		if self.name is None and self.path is not None:
			self.name = os.path.basename(self.path)


### PBXBuildPhases ###
class PBXBuildPhase(PBXNode):
	"""base class of build phase node"""
	def __init__(self, isa, guid=None):
		super(PBXBuildPhase, self).__init__(isa, guid)
		self.files = []
		self.buildActionMask = 2147483647
		self.runOnlyForDeploymentPostprocessing = 0
		self.name = None

	def node(self, isa, files=(), guid=None):
		node = PBXBuildPhase(isa, guid)
		node.files = list(files)
		return node


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
		self.name = None

	def node(self, files=(), guid=None):
		return super(PBXCopyFilesBuildPhase, self).node('PBXCopyFilesBuildPhase', files, guid)


class PBXFrameworksBuildPhase(PBXBuildPhase):
	"""docstring for PBXFrameworksBuildPhase"""
	def __init__(self, isa=None, guid=None):
		super(PBXFrameworksBuildPhase, self).__init__('PBXFrameworksBuildPhase', guid)
		self.name = 'Frameworks'

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
		self.name = 'Resources'

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


class PBXSourcesBuildPhase(PBXBuildPhase):
	"""docstring for PBXSourcesBuildPhase"""
	def __init__(self, isa=None, guid=None):
		super(PBXSourcesBuildPhase, self).__init__('PBXSourcesBuildPhase', guid)
		self.name = 'Sources'

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


class PBXTargetDependency(PBXNode):
	"""docstring for PBXTargetDependency"""
	def __init__(self, isa=None, guid=None):
		super(PBXTargetDependency, self).__init__('PBXTargetDependency', guid)
		self.target = None
		self.targetProxy = None
		self.name = None


class XCBuildConfiguration(PBXNode):
	"""docstring for XCBuildConfiguration"""
	def __init__(self, isa=None, guid=None):
		super(XCBuildConfiguration, self).__init__('XCBuildConfiguration', guid)
		self.baseConfigurationReference = None
		self.buildSettings = {}
		self.name = None


class XCConfigurationList(PBXNode):
	"""docstring for XCConfigurationList"""
	def __init__(self, isa=None, guid=None):
		super(XCConfigurationList, self).__init__('XCConfigurationList', guid)
		self.buildConfigurations = []
		self.defaultConfigurationIsVisible = None
		self.defaultConfigurationName = None


class PBXReferenceProxy(PBXNode):
	"""docstring for PBXReferenceProxy"""
	def __init__(self, isa=None, guid=None):
		super(PBXReferenceProxy, self).__init__('PBXReferenceProxy', guid)
		self.fileType = None
		self.path = None
		self.remoteRef = None
		self.sourceTree = None
		self.name = None

	def internalInit(self):
		super(PBXReferenceProxy, self).internalInit()
		if self.name is None and self.path is not None:
			self.name = os.path.basename(self.path)

# class RootElement(object):
# 	"""docstring for RootElement"""
# 	def __init__(self):
# 		super(RootElement, self).__init__()
# 		self.archiveVersion = 1
# 		self.classes = []
# 		self.objectVersion = None
# 		self.objects = {}
# 		self.rootObject = None

def isaTypeConfirmsTo(isa, confirmsTo):
	if confirmsTo == 'PBXTarget' and isa in {'PBXNativeTarget', 'PBXAggregateTarget', 'PBXLegacyTarget'}:
		return True
	if confirmsTo == 'PBXBuildPhase' and isa in {
												'PBXAppleScriptBuildPhase',
												'PBXCopyFilesBuildPhase',
												'PBXFrameworksBuildPhase',
												'PBXHeadersBuildPhase',
												'PBXResourcesBuildPhase',
												'PBXShellScriptBuildPhase',
												'PBXSourcesBuildPhase'
												}:
		return True
	return isa == confirmsTo
