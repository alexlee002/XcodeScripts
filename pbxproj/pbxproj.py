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

		from collections import OrderedDict
		projectData = json.loads(stdout, object_pairs_hook=OrderedDict)
		self.rootElement = RootElement()
		objVars = vars(self.rootElement).keys()
		for k, v in projectData.items():
			if k == 'objects':
				self.rootElement.objects = {}
				for guid, o in v.items():
					node = PBXNode.nodeFromDict(o, guid)
					if isinstance(node, PBXNode):
						self.rootElement.objects[guid] = node
			elif k in objVars:
				setattr(self.rootElement, k, v)
			else:
				Logger().warn('property: "%s" is not supported by RootElement yet.' % k)
		return self

	def fileReferenceByPath(self, path):
		for guid, node in self.rootElement.objects.items():
			if node.isa == 'PBXFileReference' and node.path == path:
				return node
		return None

	def buildFileByFileRef(self, fileRef):
		for node in self.rootElement.objects.values():
			if node.isa == 'PBXBuildFile' and node.fileRef == fileRef:
				return node
		return None

	def parentOfGroup(self, groupId):
		for node in self.rootElement.objects.values():
			if node.isa == 'PBXGroup' and guid in node.children:
				return node
			elif node.isa == 'PBXProject' and node.mainGroup == groupId:
				return node
		return None

	def fullPathOfGroup(self, groupId):
		path = ''
		if groupId in self.rootElement.objects and self.rootElement.objects[groupId].isa == 'PBXGroup':
			node = self.rootElement.objects[groupId]
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
		if groupId in self.rootElement.objects and self.rootElement.objects[groupId].isaConfirmsTo('PBXGroup'):
			groupNode = self.rootElement.objects[groupId]
		else:
			groupNode = PBXGroup().node((), groupId)
			mainGroupId = self.rootObject.mainGroup
			if not mainGroupId in self.rootElement.objects or self.rootElement.objects[mainGroupId].isa != 'PBXGroup':
				self.rootObject.mainGroup = groupId
			else:
				self.rootElement.objects[mainGroupId].children.append(groupNode.guid)
			self.rootElement.objects[groupId] = groupNode

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
			self.rootElement.objects[fileRefNode.guid] = fileRefNode
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
				self.rootElement.objects[buildFileNode.guid] = buildFileNode

		#step 3:PBXGroup
		groupNode.children.append(fileRefNode.guid)

		#step 4: PBXNativeTarget
		if targetId in self.rootElement.objects and self.rootElement.objects[targetId].isaConfirmsTo('PBXTarget'):
			targetNode = self.rootElement.objects[targetId]
		if not targetNode:
			Logger().error('project:"%s" not found target:%s' % (self.projectPath, targetId))
			sys.exit(1)

		#step 5: PBXSourcesBuildPhase
		if buildFileNode is not None:
			buildPhaseNode = None
			for guid in targetNode.buildPhases:
				if guid in self.rootElement.objects and self.rootElement.objects[guid].isaConfirmsTo('PBXBuildPhase'):
					buildPhaseNode = self.rootElement.objects[guid]
					break
			if not buildPhaseNode:
				if self.isSourcecodeFile(realPath):
					buildPhaseNode = PBXSourcesBuildPhase().node((buildFileNode.guid))
				else:
					buildPhaseNode = PBXResourcesBuildPhase().node((buildFileNode.guid))
				targetNode.buildPhases.append(buildPhaseNode.guid)
				self.rootElement.objects[buildPhaseNode.guid] = buildPhaseNode
			else:
				buildPhaseNode.files.append(buildFileNode.guid)
		return self

	def addFramework(self, path, groupId=None):
		pass

	def writeToFile(self, filePath=None):
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

		def _displayNameForNode(node):
			if node.isaConfirmsTo('PBXBuildFile'):
				refNode = self.rootElement.objects[node.fileRef] if node.fileRef in self.rootElement.objects else None
				return _displayNameForNode(refNode)
			comment = None
			if node is not None and isinstance(node, PBXNode) and str(node.guid) in self.rootElement.objects:
				#refNode = self.rootElement.objects[str(valObj)]
				varNames = vars(node).keys()
				comment = node._al_displayName if comment is None and '_al_displayName' in varNames else comment
				comment = node.name if comment is None and 'name' in varNames else comment
				comment = node.path if comment is None and 'path' in varNames else comment
				comment = node.isa if comment is None and 'isa' in varNames else comment
			return comment if comment is not None and len(comment) > 0 else None

		def _printCommentForValue(valObj):
			comment = None
			refNode = self.rootElement.objects[str(valObj)] if str(valObj) in self.rootElement.objects else None
			if refNode is not None:
				comment = _displayNameForNode(refNode)
				parentComment = None
				if 'isa' in vars(refNode) and refNode.isa == 'PBXBuildFile':
					buildPhaseNode = None
					for node in self.rootElement.objects.values():
						if node.isaConfirmsTo('PBXBuildPhase') and str(valObj) in node.files:
							buildPhaseNode = node
							break
					if buildPhaseNode is not None:
						parentComment = _displayNameForNode(buildPhaseNode)
				if comment is not None and parentComment is not None:
					comment = '%s in %s' % (comment, parentComment)
			return '' if comment is None or len(comment) == 0 else ' /* %s */' % comment

		def _printObject(obj, ident, outputLines, printOuterBrackets=False, inSingleLine=False, isBegining=True):
			from collections import OrderedDict
			needIdent = printOuterBrackets and inSingleLine or isBegining and printOuterBrackets or inSingleLine and isBegining

			objType = type(obj)
			if objType is str or objType is unicode:
				#outputLines.append(_printIdent(ident if isBegining else 0))
				outputLines.append('%s%s' % (_canonicalStringValue(obj), _printCommentForValue(obj)))

			elif isinstance(obj, dict) or isinstance(obj, OrderedDict):
				needIdent = needIdent and len(obj) > 0
				outputLines.append(_printIdent(ident if needIdent else 0))

				outputLines.append('{' if printOuterBrackets else '')
				outputLines.append('\n' if not inSingleLine and printOuterBrackets else '')

				sortedItems = sorted(obj.items(), key=lambda e: 0 if e[0] == 'isa' else e[0])
				counter = len(sortedItems)
				for key, val in sortedItems:
					counter -= 1
					if printOuterBrackets and isBegining and not inSingleLine:
						ident += 1
					keyStr = _canonicalStringValue(key) if key else ''
					outputLines.append('%s' % ('' if inSingleLine else _printIdent(ident)))
					outputLines.append('%s%s = ' % (keyStr, _printCommentForValue(keyStr)))
					_printObject(val, (ident + 1) if not inSingleLine else 0, outputLines, printOuterBrackets=True, inSingleLine=inSingleLine, isBegining=False)
					outputLines.append(';')
					if inSingleLine:
						outputLines.append(' ' if counter > 0 else '')
					else:
						outputLines.append('\n' if printOuterBrackets else '')
				if printOuterBrackets:
					outputLines.append('%s}' % ('' if inSingleLine else _printIdent(ident - (1 if len(sortedItems) > 0 else 0))))

			elif isinstance(obj, list) or isinstance(obj, tuple) or isinstance(obj, set):
				needIdent = needIdent and len(obj) > 0
				outputLines.append(_printIdent(ident if needIdent else 0))

				outputLines.append('(' if printOuterBrackets else '')
				outputLines.append('\n' if not inSingleLine and printOuterBrackets else '')

				counter = len(obj)
				for item in obj:
					counter -= 1
					if printOuterBrackets and isBegining and not inSingleLine:
						ident += 1
					outputLines.append('%s' % ('' if inSingleLine else _printIdent(ident)))
					_printObject(item, (ident + 1) if not inSingleLine else 0, outputLines, printOuterBrackets=True, inSingleLine=inSingleLine, isBegining=False)
					outputLines.append(',')
					if inSingleLine:
						outputLines.append(' ' if counter > 0 else '')
					else:
						outputLines.append('\n')
				if printOuterBrackets:
					outputLines.append('%s)' % ('' if inSingleLine else _printIdent(ident - (1 if len(obj) > 0 else 0))))

		outFile = filePath if filePath is not None else self.pbxprojPath
		with open(outFile, 'w') as writer:
			writer.write('// !$*UTF8*$!\n')
			writer.write('{\n')
			#sortedObjects = sorted(self.rootElement.items(), key=lambda e: e[1].isa)
			for name, obj in sorted(self.rootElement.toDict().items(), key=lambda e: e[0]):
				if name == 'objects':
					writer.write('\tobjects = {\n')
					currentType = None
					for guid, node in sorted(obj.items(), key=lambda e: e[1].isa):
						if currentType != node.isa:
							if currentType is not None:
								writer.write('/* End %s section */\n' % currentType)
							writer.write('\n/* Begin %s section */\n' % node.isa)
						currentType = node.isa

						lines = []
						singleLineNodes = {'PBXBuildFile', 'PBXFileReference'}
						_printObject(node.toDict(), 2, lines, inSingleLine=(node.isa in singleLineNodes), printOuterBrackets=False)
						lines.append('\n')
						writer.writelines(lines)
					writer.write('/* End %s section */\n' % currentType)
					writer.write('\t};\n')
				else:
					lines = []
					_printObject(obj, 1, lines, inSingleLine=False, printOuterBrackets=True)
					writer.write('\t%s = %s;\n' % (_canonicalStringValue(name), ''.join(lines)))
			writer.write('}\n')

if __name__ == '__main__':
	#/Users/baidu/workspace/testing/netdisk/netdisk/netdisk_iphone/netdisk_iPhone.xcodeproj
	#/Users/baidu/workspace/testing/TestProj/TestProj.xcodeproj

	#/Users/baidu/Desktop/test1.xcodeproj/project.pbxproj

	XcodeProject().parseXcodeProject('/Users/baidu/workspace/testing/TestProj1/TestProj1.xcodeproj').writeToFile('/Users/baidu/Desktop/test1.xcodeproj/project.pbxproj')
