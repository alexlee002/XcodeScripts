#!/usr/bin/python
#encoding:utf-8
#Filename: pbxproj.py

import os
import sys
import subprocess
import json
import re

mymoduleRoot = os.path.join(os.path.dirname(__file__), "..")
if not mymoduleRoot in sys.path:
	sys.path.append(mymoduleRoot)

import utils
from utils.logger import Logger
from utils.functions import *
from pbxnode import *


######################################################################################
class XcodeProject(object):
	"""Xcode project file(pbxproj) parser and editor"""
	def __init__(self):
		super(XcodeProject, self).__init__()

	def parseXcodeProject(self, pbxprojPath):
		self.pbxprojPath = os.path.normpath(os.path.abspath(pbxprojPath))
		isValid = os.path.isdir(self.pbxprojPath) and os.path.splitext(self.pbxprojPath)[1] == '.xcodeproj'
		if not isValid:
			Logger().error('"%s" is not a valid Xcode project path.' % pbxprojPath)
			sys.exit(1)
		self.projectHome = os.path.dirname(self.pbxprojPath)

		p = subprocess.Popen(['/usr/bin/plutil', '-convert', 'json', '-o', '-', os.path.join(self.pbxprojPath, 'project.pbxproj')], stdout=subprocess.PIPE)
		stdout, stderr = p.communicate()
		if p.returncode != 0:
			Logger().error('Can not parse project file')
			Logger().verbose(stdout)
			sys.exit(1)

		projectData = json.loads(stdout)
		self.archiveVersion = utils.functions.extractObjectFromDictForKey(projectData, 'archiveVersion')
		self.classes = utils.functions.extractObjectFromDictForKey(projectData, 'classes')
		self.objectVersion = utils.functions.extractObjectFromDictForKey(projectData, 'objectVersion')
		rootObjectId = utils.functions.extractObjectFromDictForKey(projectData, 'rootObject')

		objects = utils.functions.extractObjectFromDictForKey(projectData, 'objects')
		if type(objects) is not dict:
			return

		self.objects = {}
		for guid, o in objects.items():
			node = PBXNode.nodeFromDict(o, guid)
			if isinstance(node, PBXNode):
				self.objects[guid] = node

		if rootObjectId in self.objects and self.objects[rootObjectId].isa == 'PBXProject':
			self.rootObject = self.objects[rootObjectId]
		else:
			Logger().error('Can not parse project file: not found root object')
			sys.exit(1)
		return self

	def fileReferenceByPath(self, path):
		for guid, node in self.objects.items():
			if node.isa == 'PBXFileReference' and node.path == path:
				return node
		return None

	def buildFileByFileRef(self, fileRef):
		for node in self.objects.values():
			if node.isa == 'PBXBuildFile' and node.fileRef == fileRef:
				return node
		return None

	def parentOfGroup(self, groupId):
		for node in self.objects.values():
			if node.isa == 'PBXGroup' and guid in node.children:
				return node
			elif node.isa == 'PBXProject' and node.mainGroup == groupId:
				return node
		return None

	def fullPathOfGroup(self, groupId):
		path = ''
		if groupId in self.objects and self.objects[groupId].isa == 'PBXGroup':
			node = self.objects[groupId]
			path = node.path if node.path else ''

		parent = self.parentOfGroup(groupId)
		while parent.guid != self.rootObject.guid:
			if parent.path is not None:
				path = os.path.join(parent.path, path)
		return path

	def isSourcecodeFile(self, filePath):
		ext = os.path.splitext(path)[1].lower()
		return ext in FILETYPE_BY_EXT and utils.functions.stringHasPrefix(FILETYPE_BY_EXT[ext], 'sourcecode.')

	def isBuildableFile(self, filePath):
		ext = os.path.splitext(path)[1].lower()
		if ext in FILETYPE_BY_EXT:
			fileType = FILETYPE_BY_EXT[ext]
			if utils.functions.stringHasPrefix(fileType, 'sourcecode.') \
				or utils.functions.stringHasPrefix(fileType, 'image.') \
				or utils.functions.stringHasPrefix(fileType, 'audio.') \
				or utils.functions.stringHasPrefix(fileType, 'vedio.'):
				return True
		return False

	def addFile(self, realPath, targetId, groupId):
		ext = os.path.splitext(realPath)[1].lower()
		if groupId in self.objects and isaTypeConfirmsTo(self.objects[groupId].isa, 'PBXGroup'):
			groupNode = self.objects[groupId]
		else:
			groupNode = PBXGroup().node((), groupId)
			mainGroupId = self.rootObject.mainGroup
			if not mainGroupId in self.objects or self.objects[mainGroupId].isa != 'PBXGroup':
				self.rootObject.mainGroup = groupId
			else:
				self.objects[mainGroupId].children.append(groupNode.guid)
			self.objects[groupId] = groupNode

		groupPath = os.path.join(self.projectHome, self.fullPathOfGroup(groupId))
		if utils.functions.isSubPathOf(realPath, groupPath):
			path = realPath[len(groupPath):]
			path = path[1:] if utils.functions.stringHasPrefix(path, '/') else path
			sourceTree = '<group>'
		elif utils.functions.isSubPathOf(realPath, self.projectHome):
			path = realPath[len(self.projectHome):]
			path = path[1:] if utils.functions.stringHasPrefix(path, '/') else path
			sourceTree = 'SOURCE_ROOT'
		elif os.path.exists(realPath):
			path = realPath
			sourceTree = '<absolute>'

		isBuildableFile = self.isBuildableFile(realPath)

		#step 1: PBXFileReference
		fileRefNode = self.fileReferenceByPath(path)
		if fileRefNode is None:
			fileRefNode = PBXFileReference().node(path)
			self.objects[fileRefNode.guid] = fileRefNode
			fileRefNode.sourceTree = sourceTree
			if fileRefNode.lastKnownFileType is None and fileRefNode.explicitFileType is None:
				if os.path.isdir(realPath):
					fileRefNode.lastKnownFileType = 'folder'
				elif os.path.isfile(realPath):
					fileRefNode.lastKnownFileType = 'file'

		#step 2: PBXBuildFile
		if isBuildableFile and ext not in HEADER_FILE_EXTS:
			buildFileNode = self.buildFileByFileRef(fileRefNode.guid)
			if buildFileNode is None:
				buildFileNode = PBXBuildFile().node(fileRefNode.guid)
				self.objects[buildFileNode.guid] = buildFileNode

		#step 3:PBXGroup
		groupNode.children.append(fileRefNode.guid)

		#step 4: PBXNativeTarget
		if targetId in self.objects and isaTypeConfirmsTo(self.objects[targetId].isa, 'PBXTarget'):
			targetNode = self.objects[targetId]
		if not targetNode:
			Logger().error('project:"%s" not found target:%s' % (self.projectPath, targetId))
			sys.exit(1)

		#step 5: PBXSourcesBuildPhase
		if buildFileNode is not None:
			buildPhaseNode = None
			for guid in targetNode.buildPhases:
				if guid in self.objects and isaTypeConfirmsTo(self.objects[guid].isa, 'PBXBuildPhase'):
					buildPhaseNode = self.objects[guid]
					break
			if not buildPhaseNode:
				if self.isSourcecodeFile(realPath):
					buildPhaseNode = PBXSourcesBuildPhase().node((buildFileNode.guid))
				else:
					buildPhaseNode = PBXResourcesBuildPhase().node((buildFileNode.guid))
				targetNode.buildPhases.append(buildPhaseNode.guid)
				self.objects[buildPhaseNode.guid] = buildPhaseNode
			else:
				buildPhaseNode.files.append(buildFileNode.guid)
		return self

	def addFramework(self, path, groupId=None):
		pass

	def writeToFile(self, filePath=None):
		fileRefItems = {'PBXFileReference', 'PBXVariantGroup', 'PBXReferenceProxy', 'XCVersionGroup'}

		def _line(msg):
			return '%s\n' % msg

		def _printIdent(ident):
			string = ''
			for i in xrange(0, ident):
				string = '%s\t' % string
			return string

		def _canonicalStringValue(val):
			canonicalVal = val
			if type(val) is str or type(val) is unicode:
				if re.search('[+\-=\s<>\(\)\[\]@,;\*\$\}]', str(val)):
					val = str(val).replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"')
					canonicalVal = '"%s"' % val
				canonicalVal = '""' if len(canonicalVal) == 0 else canonicalVal
			return canonicalVal

		def _printBuildFileNode(node, ident):
			for p in self.objects.values():
				if isaTypeConfirmsTo(p.isa, 'PBXBuildPhase') and node.guid in p.files:
					parent = p
					break

			if node.fileRef in self.objects and self.objects[node.fileRef].isa in fileRefItems:
				fileRefNode = self.objects[node.fileRef]
			else:
				fileRefNode = None
			if fileRefNode is None or parent is None:
				Logger().error('illegal PBXBuildFile node, no fileRef or buildPhase:%s ' % node.guid)
				Logger().error('\tfileRef: %s' % (fileRefNode.guid if fileRefNode else 'None'))
				Logger().error('\tbuildPhase: %s' % parent.guid if parent else 'None')
				sys.exit(1)
			content = _printIdent(ident)
			content += node.guid
			content += ' /* %s in %s */' % (fileRefNode.name, parent.name)
			content += ' = {isa = %s; fileRef = %s /* %s */;' % (_canonicalStringValue(node.isa), _canonicalStringValue(node.fileRef), fileRefNode.name)
			if type(node.settings) is dict and len(node.settings) > 0:
				content += ' settings = '
				lines = []
				_printObject(node.settings, 0, lines)
				content += ''.join(lines)
				content += ';'
			content += '};'
			return content

		def _printPBXContainerItemProxy(node, ident):
			lines = [_line('%s%s /* %s */ = {' % (_printIdent(ident), node.guid, node.isa))]
			linePrefix = _printIdent(ident + 1)

			lines.append(_line('%sisa = %s;' % (linePrefix, _canonicalStringValue(node.isa))))

			if node.containerPortal == self.rootObject.guid:
				comment = 'Project object'
			elif node.containerPortal in self.objects and self.objects[node.containerPortal].isa in fileRefItems:
				comment = self.objects[node.containerPortal].name
			else:
				comment = ''
			lines.append(_line('%scontainerPortal = %s /* %s */;' % (linePrefix, node.containerPortal, comment)))
			lines.append(_line('%sproxyType = %s;' % (linePrefix, _canonicalStringValue(node.proxyType))))
			lines.append(_line('%sremoteGlobalIDString = %s;' % (linePrefix, _canonicalStringValue(node.remoteGlobalIDString))))
			if node.remoteInfo is not None:
				lines.append(_line('%sremoteInfo = %s;' % (linePrefix, _canonicalStringValue(node.remoteInfo))))
			lines.append(_line('%s};\n' % _printIdent(ident)))
			return lines

		def _printPBXFileReference(node, ident):
			content = '%s%s /* %s */ = {' % (_printIdent(ident), node.guid, node.name)
			content = '%sisa = PBXFileReference;' % content
			if node.explicitFileType is not None:
				content = '%s explicitFileType = %s;' % (content, _canonicalStringValue(node.explicitFileType))
			if node.lastKnownFileType is not None:
				content = '%s lastKnownFileType = %s;' % (content, _canonicalStringValue(node.lastKnownFileType))
			if node.includeInIndex is not None:
				content = '%s includeInIndex = %s;' % (content, _canonicalStringValue(node.includeInIndex))
			if node.fileEncoding is not None:
				content = '%s fileEncoding = %s;' % (content, _canonicalStringValue(node.fileEncoding))
			if node.name != node.path:
				content = '%s name = %s;' % (content, _canonicalStringValue(node.name))
			content = '%s path = %s;' % (content, _canonicalStringValue(node.path))
			content = '%s sourceTree = %s; };' % (content, _canonicalStringValue(node.sourceTree))
			return content

		def _printBuildPhase(node, ident):
			lines = [_line('%s%s /* %s */ = {' % (_printIdent(ident), node.guid, node.name))]
			identPrefix = _printIdent(ident + 1)
			lines.append(_line('%sisa = %s;' % (identPrefix, _canonicalStringValue(node.isa))))
			lines.append(_line('%sbuildActionMask = %s;' % (identPrefix, _canonicalStringValue(node.buildActionMask))))
			lines.append(_line('%sfiles = (' % identPrefix))
			identPrefix1 = '%s\t' % identPrefix
			for f in node.files:
				buildFileNode = self.objects[f] if f in self.objects else None
				fileRefNode = self.objects[buildFileNode.fileRef] if buildFileNode and buildFileNode.fileRef in self.objects else None
				fileRefName = fileRefNode.name if fileRefNode and fileRefNode.name else None
				lines.append(_line('%s%s /* %s in %s */,' % (identPrefix1, _canonicalStringValue(f), fileRefName, node.name)))
			lines.append(_line('%s);' % identPrefix))
			lines.append(_line('%srunOnlyForDeploymentPostprocessing = %s;' % (identPrefix, node.runOnlyForDeploymentPostprocessing)))
			lines.append(_line('%s};' % _printIdent(ident)))
			return lines

		def _printPBXShellScriptBuildPhase(node, ident):
			lines = _printBuildPhase(node, ident)
			identPrefix = _printIdent(ident + 1)
			extraLines = [_line('%sinputPaths = ' % identPrefix)]
			_printObject(node.inputPaths, ident + 2, extraLines)
			extraLines.append(_line(';'))

			extraLines.append(_line('%sname = %s;' % (identPrefix, _canonicalStringValue(node.name))))

			extraLines.append(_line('%soutputPaths = ' % identPrefix))
			_printObject(node.outputPaths, ident + 2, extraLines)
			extraLines.append(_line(';'))

			extraLines.append(_line('%sshellPath = %s;' % (identPrefix, _canonicalStringValue(node.shellPath))))
			extraLines.append(_line('%sshellScript = %s;' % (identPrefix, _canonicalStringValue(node.shellScript))))

			for l in extraLines:
				lines.insert(len(lines)-1, l)
			return lines

		def _printCopyFileResourceBuildPhase(node, ident):
			lines = _printBuildPhase(node, ident)
			identPrefix = _printIdent(ident + 1)
			extraLines = [_line('%sdstPath = %s;' % (identPrefix, _canonicalStringValue(node.dstPath)))]
			extraLines.append(_line('%sdstSubfolderSpec = %s;' % (identPrefix, _canonicalStringValue(node.dstSubfolderSpec))))
			for l in extraLines:
				lines.insert(len(lines)-1, l)
			return lines

		def _printPBXGroup(node, ident):
			content = '%s%s' % (_printIdent(ident), node.guid)
			if node.name is not None:
				content = '%s /* %s */' % (content, node.name)
			content = '%s = {' % content

			lines = [_line(content)]
			identPrefix = _printIdent(ident + 1)
			lines.append(_line('%sisa = %s;' % (identPrefix, _canonicalStringValue(node.isa))))
			lines.append(_line('%schildren = (' % identPrefix))
			identPrefix1 = '%s\t' % identPrefix
			for c in node.children:
				o = self.objects[c] if c in self.objects else None
				childName = o.name if o and o.name else None
				if childName is None:
					childName = o.path if o and o.path else None
				childLine = '%s%s' % (identPrefix1, _canonicalStringValue(c))
				if childName is not None:
					childLine = '%s /* %s */' % (childLine, childName)
				lines.append(_line('%s,' % childLine))
			lines.append(_line('%s);' % identPrefix))
			if node.name is not None and node.name != node.path:
				lines.append(_line('%sname = %s;' % (identPrefix, _canonicalStringValue(node.name))))
			if node.path is not None:
				lines.append(_line('%spath = %s;' % (identPrefix, _canonicalStringValue(node.path))))

			lines.append(_line('%ssourceTree = %s;' % (identPrefix, _canonicalStringValue(node.sourceTree))))
			lines.append(_line('%s};' % _printIdent(ident)))
			return lines

		def _printPBXNativeTarget(node, ident):
			lines = [_line('%s%s /* %s */ = {' % (_printIdent(ident), node.guid, node.name))]
			identPrefix = _printIdent(ident + 1)
			lines.append(_line('%sisa = %s;' % (identPrefix, _canonicalStringValue(node.isa))))
			lines.append(_line('%sbuildConfigurationList = %s /* Build configuration list for PBXNativeTarget "%s" */;' % (identPrefix, _canonicalStringValue(node.buildConfigurationList), node.name)))

			lines.append(_line('%sbuildPhases = (' % identPrefix))
			identPrefix1 = '%s\t' % identPrefix
			for b in node.buildPhases:
				string = '%s%s' % (identPrefix1, _canonicalStringValue(b))
				o = self.objects[b] if b in self.objects else None
				name = o.name if o and o.name else None
				if name is not None:
					string = '%s /* %s */' % (string, name)
				lines.append(_line('%s,' % string))
			lines.append(_line('%s);' % identPrefix))

			lines.append(_line('%sbuildRules = (' % identPrefix))
			for b in node.buildRules:
				lines.append(_line('%s%s,' % (identPrefix1, _canonicalStringValue(b))))
			lines.append(_line('%s);' % identPrefix))

			lines.append(_line('%sdependencies = (' % identPrefix))
			for d in node.dependencies:
				o = self.objects[d] if d in self.objects else None
				if o is not None:
					string = '%s%s /* %s */,' % (identPrefix1, _canonicalStringValue(d), o.isa)
				else:
					string = '%s%s,' % (identPrefix1, _canonicalStringValue(d))
				lines.append(_line(string))
			lines.append(_line('%s);' % identPrefix))

			lines.append(_line('%sname = %s;' % (identPrefix, _canonicalStringValue(node.name))))
			lines.append(_line('%sproductName = %s;' % (identPrefix, _canonicalStringValue(node.productName))))
			pr = self.objects[node.productReference] if node.productReference in self.objects else None
			if pr is not None:
				lines.append(_line('%sproductReference = %s /* %s */;' % (identPrefix, _canonicalStringValue(node.productReference), pr.name)))
			else:
				lines.append(_line('%sproductReference = %s;' % (identPrefix, _canonicalStringValue(node.productReference))))
			lines.append(_line('%sproductType = %s;' % (identPrefix, _canonicalStringValue(node.productType))))
			lines.append(_line('%s};' % _printIdent(ident)))
			return lines

		def _printPBXProject(node, ident):
			lines = [_line('%s%s /* Project object */ = {' % (_printIdent(ident), node.guid))]
			identPrefix = _printIdent(ident + 1)
			lines.append(_line('%sisa = %s;' % (identPrefix, _canonicalStringValue(node.isa))))
			lines.append(_line('%sattributes = ' % identPrefix))
			_printObject(node.attributes, ident + 2, lines)
			lines.append(_line(';'))
			lines.append(_line('%sbuildConfigurationList = %s /* Build configuration list for PBXProject */;' % (identPrefix, _canonicalStringValue(node.buildConfigurationList))))
			lines.append(_line('%scompatibilityVersion = %s;' % (identPrefix, _canonicalStringValue(node.compatibilityVersion))))
			if node.developmentRegion is not None:
				lines.append(_line('%sdevelopmentRegion = %s;' % (identPrefix, _canonicalStringValue(node.developmentRegion))))
			lines.append(_line('%shasScannedForEncodings = %s;' % (identPrefix, node.hasScannedForEncodings)))
			if node.knownRegions is not None:
				lines.append(_line('%sknownRegions = ' % identPrefix))
				_printObject(node.knownRegions, ident + 2, lines)
				lines.append(_line(';'))
			lines.append(_line('%smainGroup = %s;' % (identPrefix, _canonicalStringValue(node.mainGroup))))
			lines.append(_line('%sproductRefGroup = %s /* Products */;' % (identPrefix, _canonicalStringValue(node.productRefGroup))))
			lines.append(_line('%sprojectDirPath = %s;' % (identPrefix, _canonicalStringValue(node.projectDirPath))))
			if node.projectReferences is not None and len(node.projectReferences) > 0:
				lines.append(_line('%sprojectReferences = ' % identPrefix))
				_printObject(node.projectReferences, ident + 2, lines)
				lines.append(_line(';'))
			lines.append(_line('%sprojectRoot = %s;' % (identPrefix, _canonicalStringValue(node.projectRoot))))
			if node.targets is not None:
				lines.append(_line('%stargets = ' % identPrefix))
				_printObject(node.targets, ident + 2, lines)
				lines.append(_line(';'))
			lines.append(_line('%s};' % _printIdent(ident)))
			return lines

		def _printPBXReferenceProxy(node, ident):
			lines = [_line('%s%s /* %s */ = {' % (_printIdent(ident), node.guid, node.name))]
			identPrefix = _printIdent(ident + 1)
			lines.append(_line('%sisa = %s;' % (identPrefix, _canonicalStringValue(node.isa))))
			lines.append(_line('%sfileType = %s;' % (identPrefix, _canonicalStringValue(node.fileType))))
			lines.append(_line('%spath = %s;' % (identPrefix, _canonicalStringValue(node.path))))
			if node.name is not None and node.name != node.path:
				lines.append(_line('%sname = %s;' % (identPrefix, _canonicalStringValue(node.name))))
			o = self.objects[node.remoteRef] if node.remoteRef in self.objects else None
			if o is not None:
				lines.append(_line('%sremoteRef = %s /* %s */;' % (identPrefix, _canonicalStringValue(node.remoteRef), o.isa)))
			else:
				lines.append(_line('%sremoteRef = %s;' % (identPrefix, _canonicalStringValue(node.remoteRef))))
			lines.append(_line('%ssourceTree = %s;' % (identPrefix, _canonicalStringValue(node.sourceTree))))
			lines.append(_line('%s};' % _printIdent(ident)))
			return lines

		def _printPBXTargetDependency(node, ident):
			lines = [_line('%s%s /* %s */ = {' % (_printIdent(ident), node.guid, node.isa))]
			identPrefix = _printIdent(ident + 1)
			lines.append(_line('%sisa = %s;' % (identPrefix, _canonicalStringValue(node.isa))))
			lines.append(_line('%sname = %s;' % (identPrefix, _canonicalStringValue(node.name))))
			lines.append(_line('%stargetProxy = %s /* %s */;' % (identPrefix, node.targetProxy, self.objects[node.targetProxy].isa)))
			lines.append(_line('%s};' % _printIdent(ident)))
			return lines

		def _printPBXVariantGroup(node, ident):
			lines = [_line('%s%s /* %s */ = {' % (_printIdent(ident), node.guid, node.name))]
			identPrefix = _printIdent(ident + 1)
			lines.append(_line('%sisa = %s;' % (identPrefix, _canonicalStringValue(node.isa))))
			lines.append(_line('%schildren = (' % identPrefix))
			identPrefix1 = '%s\t' % identPrefix
			for c in node.children:
				o = self.objects[c] if c in self.objects and self.objects[c].isa in fileRefItems else None
				if o and o.name:
					lines.append(_line('%s%s /* %s */,' % (identPrefix1, _canonicalStringValue(c), o.name)))
				else:
					lines.append(_line('%s%s,' % (identPrefix1, _canonicalStringValue(c))))
			lines.append(_line('%s);' % identPrefix))

			lines.append(_line('%sname = %s;' % (identPrefix, _canonicalStringValue(node.name))))
			lines.append(_line('%ssourceTree = %s;' % (identPrefix, _canonicalStringValue(node.sourceTree))))
			lines.append(_line('%s};' % _printIdent(ident)))
			return lines

		def _printXCBuildConfiguration(node, ident):
			lines = [_line('%s%s /* %s */ = {' % (_printIdent(ident), node.guid, node.name))]
			identPrefix = _printIdent(ident + 1)
			lines.append(_line('%sisa = %s;' % (identPrefix, _canonicalStringValue(node.isa))))

			if node.baseConfigurationReference is not None:
				o = self.objects[node.baseConfigurationReference] if node.baseConfigurationReference in self.objects and self.objects[node.baseConfigurationReference].isa in fileRefItems else None
				if o and o.name:
					lines.append(_line('%sbaseConfigurationReference = %s /* %s */;' % (identPrefix, _canonicalStringValue(node.isa), o.name)))
				else:
					lines.append(_line('%sbaseConfigurationReference = %s;' % (identPrefix, _canonicalStringValue(node.isa))))
			lines.append(_line('%sbuildSettings = ' % identPrefix))
			_printObject(node.buildSettings, ident + 2, lines)
			lines.append(_line(';'))
			lines.append(_line('%sname = %s;' % (identPrefix, _canonicalStringValue(node.name))))
			lines.append(_line('%s};' % _printIdent(ident)))
			return lines

		def _printXCConfigurationList(node, ident):
			if self.rootObject.buildConfigurationList == node.guid:
				comment = 'PBXProject'
			else:
				for o in self.objects.values():
					if isaTypeConfirmsTo(o.isa, 'PBXTarget') and o.buildConfigurationList is not None:
						comment = '%s "%s"' % (o.isa, o.name)
						break
			lines = [_line('%s%s /* Build configuration list for %s */ = {' % (_printIdent(ident), node.guid, comment))]
			identPrefix = _printIdent(ident + 1)
			lines.append(_line('%sisa = %s;' % (identPrefix, _canonicalStringValue(node.isa))))
			lines.append(_line('%sbuildConfigurations = (' % identPrefix))
			identPrefix1 = '%s\t' % identPrefix
			for bc in node.buildConfigurations:
				o = self.objects[bc] if bc in self.objects and self.objects[bc].isa == 'XCBuildConfiguration' else None
				if o and o.name:
					lines.append(_line('%s%s /* %s */,' % (identPrefix1, _canonicalStringValue(bc), o.name)))
				else:
					lines.append(_line('%s%s,' % (identPrefix1, _canonicalStringValue(bc))))
			lines.append(_line('%s);' % identPrefix))
			lines.append(_line('%sdefaultConfigurationIsVisible = %s;' % (identPrefix, _canonicalStringValue(node.defaultConfigurationIsVisible))))
			lines.append(_line('%sdefaultConfigurationName = %s;' % (identPrefix, _canonicalStringValue(node.defaultConfigurationName))))
			lines.append(_line('%s};' % _printIdent(ident)))
			return lines

		def _printVersionGroups(node, ident):
			lines = [_line('%s%s /* %s */ = {' % (_printIdent(ident), node.guid, node.name))]
			identPrefix = _printIdent(ident + 1)
			lines.append(_line('%sisa = %s;' % (identPrefix, _canonicalStringValue(node.isa))))
			lines.append(_line('%schildren = (' % identPrefix))
			identPrefix1 = '%s\t' % identPrefix
			for c in node.children:
				o = self.objects[c] if c in self.objects and self.objects[c].isa in fileRefItems else None
				if o and o.name:
					lines.append(_line('%s%s /* %s */,' % (identPrefix1, _canonicalStringValue(c), o.name)))
				else:
					lines.append(_line('%s%s,' % (identPrefix1, _canonicalStringValue(c))))
			lines.append(_line('%s);' % identPrefix))

			lines.append(_line('%scurrentVersion = %s /* %s */;' % (identPrefix, _canonicalStringValue(node.isa), node.name)))
			lines.append(_line('%spath = %s;' % (identPrefix, _canonicalStringValue(node.path))))
			lines.append(_line('%ssourceTree = %s;' % (identPrefix, _canonicalStringValue(node.sourceTree))))
			lines.append(_line('%sversionGroupType = %s;' % (identPrefix, _canonicalStringValue(node.versionGroupType))))
			lines.append(_line('%s};' % _printIdent(ident)))
			return lines

		def _printObject(obj, ident, strings):
			strings = [] if strings is None else strings
			strings = list(strings) if type(strings) is tuple or type(strings) is set else strings
			strings = [str(strings)] if type(strings) is not list else strings
			t = type(obj)
			identPrefix = _printIdent(ident)
			if t is str or t is unicode:
				strings.append('%s' % _canonicalStringValue(obj))
			elif t is list or t is set or t is tuple:
				strings.append('(')
				strings.append('\n')
				strings.append(identPrefix)
				for i in obj:
					_printObject(i, ident + 1, strings)
					strings.append(',')
					strings.append('\n')
					strings.append(identPrefix)
				strings.append(')')
			elif t is dict:
				strings.append('{')
				strings.append('\n')
				strings.append(identPrefix)
				for k, v in obj.items():
					strings.append('%s = ' % _canonicalStringValue(k) if k else '')
					_printObject(v, ident + 1, strings)
					strings.append(';')
					strings.append('\n')
					strings.append(identPrefix)
				strings.append('}')
			else:
				strings.append('%s' % _canonicalStringValue(str(obj)))

		outFile = filePath if filePath is not None else self.pbxprojPath
		with open(outFile, 'w') as writer:
			#writer.write(fileHeader)
			writer.write(_line('// !$*UTF8*$!'))
			writer.write(_line('{'))
			writer.write(_line('\tarchiveVersion = %s;' % self.archiveVersion if self.archiveVersion is not None else 1))
			writer.write(_line('\tclasses = {'))
			writer.write(_line('\t};'))
			writer.write(_line('\tobjectVersion = %s;' % self.objectVersion if self.objectVersion is not None else 46))
			writer.write(_line('\tobjects = {'))
			writer.write(_line(''))

			ident = 2
			writer.write(_line('/* Begin PBXBuildFile section */'))
			for node in [node for node in self.objects.values() if node.isa == 'PBXBuildFile']:
				writer.write(_line(_printBuildFileNode(node, ident)))
			writer.write(_line('/* End PBXBuildFile section */'))

			writer.write(_line(''))
			writer.write(_line('/* Begin PBXContainerItemProxy section */'))
			for node in [node for node in self.objects.values() if node.isa == 'PBXContainerItemProxy']:
				writer.writelines(_printPBXContainerItemProxy(node, ident))
			writer.write(_line('/* End PBXContainerItemProxy section */'))

			writer.write(_line(''))
			writer.write(_line('/* Begin PBXFileReference section */'))
			for node in [node for node in self.objects.values() if node.isa == 'PBXFileReference']:
				writer.write(_line(_printPBXFileReference(node, ident)))
			writer.write(_line('/* End PBXFileReference section */'))

			frameworkPhases = [node for node in self.objects.values() if node.isa == 'PBXFrameworksBuildPhase']
			if len(frameworkPhases) > 0:
				writer.write(_line(''))
				writer.write(_line('/* Begin PBXFrameworksBuildPhase section */'))
				for node in frameworkPhases:
					writer.writelines(_printBuildPhase(node, ident))
				writer.write(_line('/* End PBXFrameworksBuildPhase section */'))

			writer.write(_line(''))
			writer.write(_line('/* Begin PBXGroup section */'))
			for node in [node for node in self.objects.values() if node.isa == 'PBXGroup']:
				writer.writelines(_printPBXGroup(node, ident))
			writer.write(_line('/* End PBXGroup section */'))

			writer.write(_line(''))
			writer.write(_line('/* Begin PBXNativeTarget section */'))
			for node in [node for node in self.objects.values() if node.isa == 'PBXNativeTarget']:
				writer.writelines(_printPBXNativeTarget(node, ident))
			writer.write(_line('/* End PBXNativeTarget section */'))

			writer.write(_line(''))
			writer.write(_line('/* Begin PBXProject section */'))
			writer.writelines(_printPBXProject(self.rootObject, ident))
			writer.write(_line('/* End PBXProject section */'))

			writer.write(_line(''))
			writer.write(_line('/* Begin PBXReferenceProxy section */'))
			for node in [node for node in self.objects.values() if node.isa == 'PBXReferenceProxy']:
				writer.writelines(_printPBXReferenceProxy(node, ident))
			writer.write(_line('/* End PBXReferenceProxy section */'))

			# PBXCopyFilesBuildPhase
			copyResourceBuildPhases = [node for node in self.objects.values() if node.isa == 'PBXCopyFilesBuildPhase']
			if len(copyResourceBuildPhases) > 0:
				writer.write(_line(''))
				writer.write(_line('/* Begin PBXCopyFilesBuildPhase section */'))
				for node in copyResourceBuildPhases:
					writer.writelines(_printCopyFileResourceBuildPhase(node, ident))
				writer.write(_line('/* End PBXCopyFilesBuildPhase section */'))

			writer.write(_line(''))
			writer.write(_line('/* Begin PBXResourcesBuildPhase section */'))
			for node in [node for node in self.objects.values() if node.isa == 'PBXResourcesBuildPhase']:
				writer.writelines(_printBuildPhase(node, ident))
			writer.write(_line('/* End PBXResourcesBuildPhase section */'))

			shellscriptPhases = [node for node in self.objects.values() if node.isa == 'PBXShellScriptBuildPhase']
			if len(shellscriptPhases) > 0:
				writer.write(_line(''))
				writer.write(_line('/* Begin PBXShellScriptBuildPhase section */'))
				for node in shellscriptPhases:
					writer.writelines(_printPBXShellScriptBuildPhase(node, ident))
				writer.write(_line('/* End PBXShellScriptBuildPhase section */'))

			writer.write(_line(''))
			writer.write(_line('/* Begin PBXSourcesBuildPhase section */'))
			for node in [node for node in self.objects.values() if node.isa == 'PBXSourcesBuildPhase']:
				writer.writelines(_printBuildPhase(node, ident))
			writer.write(_line('/* End PBXSourcesBuildPhase section */'))

			targtDependencies = [node for node in self.objects.values() if node.isa == 'PBXTargetDependency']
			if len(targtDependencies) > 0:
				writer.write(_line(''))
				writer.write(_line('/* Begin PBXTargetDependency section */'))
				for node in targtDependencies:
					writer.writelines(_printPBXTargetDependency(node, ident))
				writer.write(_line('/* End PBXTargetDependency section */'))

			variantGroups = [node for node in self.objects.values() if node.isa == 'PBXVariantGroup']
			if len(variantGroups) > 0:
				writer.write(_line(''))
				writer.write(_line('/* Begin PBXVariantGroup section */'))
				for node in variantGroups:
					writer.writelines(_printPBXVariantGroup(node, ident))
				writer.write(_line('/* End PBXVariantGroup section */'))

			buildConfigs = [node for node in self.objects.values() if node.isa == 'XCBuildConfiguration']
			if len(buildConfigs) > 0:
				writer.write(_line(''))
				writer.write(_line('/* Begin XCBuildConfiguration section */'))
				for node in buildConfigs:
					writer.writelines(_printXCBuildConfiguration(node, ident))
				writer.write(_line('/* End XCBuildConfiguration section */'))

			xcconfigList = [node for node in self.objects.values() if node.isa == 'XCConfigurationList']
			if len(xcconfigList) > 0:
				writer.write(_line(''))
				writer.write(_line('/* Begin XCConfigurationList section */'))
				for node in xcconfigList:
					writer.writelines(_printXCConfigurationList(node, ident))
				writer.write(_line('/* End XCConfigurationList section */'))

			versionGroups = [node for node in self.objects.values() if node.isa == 'XCVersionGroup']
			if len(versionGroups) > 0:
				writer.write(_line(''))
				writer.write(_line('/* Begin XCVersionGroup section */'))
				for node in versionGroups:
					writer.writelines(_printVersionGroups(node, ident))
				writer.write(_line('/* End XCVersionGroup section */'))

			writer.write(_line('\t};'))
			writer.write(_line('\trootObject = %s /* Project object */;' % self.rootObject.guid))
			writer.write(_line('}'))



if __name__ == '__main__':
	#/Users/baidu/workspace/testing/netdisk/netdisk/netdisk_iphone/netdisk_iPhone.xcodeproj
	#/Users/baidu/workspace/testing/TestProj/TestProj.xcodeproj
	XcodeProject().parseXcodeProject('/Users/baidu/workspace/testing/netdisk/netdisk/netdisk_iphone/netdisk_iPhone.xcodeproj').writeToFile('/Users/baidu/Desktop/test1.xcodeproj/project.pbxproj')
