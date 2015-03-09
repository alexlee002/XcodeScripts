#!/usr/bin/python
#encoding:utf-8
#Filename: images_build.py

import os
import sys

mymoduleRoot = os.path.join(os.path.dirname(__file__), "..")
if not mymoduleRoot in sys.path:
	sys.path.append(mymoduleRoot)

import utils
from images_res import ImagesResource
from utils.logger import Logger
from utils.template_function import *
from utils.functions import *
from pbxproj.pbxnode import *
from pbxproj.pbxproj import *


##################################################################################################
class ImagesResourceBuilder(object):
	def __init__(self, xcproj):
		super(ImagesResourceBuilder, self).__init__()
		self.xcproj = xcproj

	def buildImageResources(self, target):
		#imagefiles, imagesets = ImagesResource(self.xcproj).allImageObjects()
		imagesets, conflicts = ImagesResource(self.xcproj).imagesets(target)
		if len(conflicts) > 0:
			self._printNameConflicts(conflicts)
			sys.exit(1)
		self._buildImagesets(target, imagesets)

	def _printNameConflicts(self, conflicts):
		lines = ['image name conflicts found:\n']
		for name, paths in conflicts:
			lines.append('%s =>\n\t' % name)
			lines.append('\n\t'.join(paths))
		Logger().error(''.join(lines))

	def _buildImagesets(self, target, imagesets):
		from xcassets import ImageModel

		resourceName = 'imagesets'
		headerfile, sourcefile = self._prepareResourceOutfiles('', bundleName)
		headerLines = [] if os.path.isfile(headerfile) else self._genFileHeaderComments(os.path.basename(headerfile), target)
		sourceLines = [] if os.path.isfile(sourcefile) else self._genFileHeaderComments(os.path.basename(sourcefile), target)

		className = self._outfileName(resourceName, bundleName)
		headerLines.append('@interface %s : NSObject' % className)
		sourceLines.append('@implementation %s' % className)

		for imgName, path in imagesets.items():
			imagesetsName = os.path.splitext(os.path.basename(path))[0]
			propertyName = ImageModel.canonicalImageNameWitName(imagesetsName)
			headerLines.append('@property(readonly, nonatomic) NSString *%s;' % propertyName.title())

			sourceLines.append('- (NSString *)%s { return @"%s"; }' % (propertyName.title(), imagesetsName))

		headerLines.append('@end')
		sourceLines.append('@end')

		tmpHeaderFile = os.path.join(self.xcproj.projectHome, '%s.tmp' % headerfile)
		tmpSourceFile = os.path.join(self.xcproj.projectHome, '%s.tmp' % sourcefile)
		try:
			with open(tmpHeaderFile, 'wb') as headerFp:
				headerFp.writelines([l + '\n' for l in headerLines])
			with open(tmpSourceFile, 'wb') as sourceFp:
				sourceFp.writelines([l + '\n' for l in sourceLines])
			os.rename(tmpHeaderFile, os.path.join(self.xcproj.projectHome, headerfile))
			os.rename(tmpSourceFile, os.path.join(self.xcproj.projectHome, sourcefile))
		except Exception, e:
			Logger().error('Unable to generate resources: "imagesets" in bundle:%s, error:%s' % (bundleName, e))
			os.remove(tmpHeaderFile)
			os.remove(tmpSourceFile)

	def _propertiesOfClass(self, className, filePath):
		import re
		properties = []
		contents = utils.functions.trimComment(filePath).splitlines()
		isTargetRegion = False
		for line in contents:
			if not isTargetRegion:
				m = re.match('^\s*@interface\s+%s\s*:\s*\w[\w\d_]*\s*' % className, line, re.IGNORECASE)
				if m and m.group():
					isTargetRegion = True
			elif isTargetRegion:
				m = re.match('^\s*@end\s*', line)
				if m and m.group():
					break

				m = re.match('\s*@property\s*\([\w,\s]+\)\s*(\w[\w\d_]*\s*\*?)\s*(\w[\w\d_]*);', line, re.IGNORECASE)
				if m and m.group():
					propertyClass, propertyName = m.groups()
					propertyClass = re.sub(r'\s+\*', '*', propertyClass)
					properties.append((propertyClass, propertyName))
		return properties

	def _updateBundleClass(self, resourceName, resourceClassName, action='add', bundleName='main'):

		def __writeBundleFiles(properties, headerfile, sourcefile):
			headerLines = self._genFileHeaderComments(headerfile, '')
			

		bundleClassName = self._outfileName('', bundleName)
		bundleHeaderFile, bundleSourceFile = self._prepareResourceOutfiles('', bundleName)
		bundleChassProperties = self._propertiesOfClass(bundleClassName, os.path.join(self.xcproj.projectHome, headerOutfile))
		propertyPaires = (resourceClassName, resourceName)
		if propertyPaires in bundleChassProperties:
			if action == 'add' and bundleName == 'main':
				return
			elif action == 'delete':
				bundleChassProperties.remove(propertyPaires)
		elif action == 'add':
			bundleChassProperties.append(propertyPaires)
		elif action == 'delete':
			return

		if len(bundleChassProperties) == 0:
			if bundleName == 'main':


		pass

	def _genFileHeaderComments(self, fileName, targetName):
		from datetime import date
		from datetime import datetime

		headerLines = ['//']
		headerLines.append('// %s' % fileName)
		headerLines.append('// %s' % targetName)
		headerLines.append('//')
		headerLines.append('// Created by XcodeScripts automatically on %s.' % date.isoformat(date.today()))
		headerLines.append('// Copyright (c) %s %s. All rights reserved.' % (datetime.now().strftime('%Y'), self.xcproj.organizationName()))
		headerLines.append('//')
		headerLines.extend(['', ''])  # 2 lines
		return headerLines

	def _sourcePhaseForTarget(self, target):
		target = self.xcproj.targetNamed(target)
		if not target:
			Logger().error('target "%s" not found in project "%s".' % (target, self.xcproj.projectHome))
			sys.exit(1)
		buildPhase = None
		for nodeId in target.buildPhases:
			node = self.xcproj.nodeWithGuid(nodeId)
			if node and node.isaConfirmsTo('PBXSourcesBuildPhase'):
				buildPhase = node
				break
		return buildPhase

	def _pbxnodeForResorceFiles(self, target):
		outputDirName = 'auto_gen'
		mainFileName = 'main.m'
		mainFilePBXNode = None
		buildPhase = self._sourcePhaseForTarget(target)
		if buildPhase:
			for node in buildPhase.files:
				if node.isaConfirmsTo('PBXBuildFile'):
					node = self.xcproj.nodeWithGuid(node.fileRef)
					if node and node.isaConfirmsTo('PBXFileReference') and os.path.basename(node.path) == mainFileName:
						mainFilePBXNode = node
						break
		if mainFilePBXNode:
			parentGroup = self.xcproj.parentObjectForNode(mainFilePBXNode.guid)
			if not parentGroup:
				Logger().error('Can not fine the group node for "main.m" in target: %s' % target)
				sys.exit(1)
			absPath = self.xcproj.absolutePathForNode(parentGroup)
			if not os.path.isdir(absPath):
				Logger().error('path:"%s" for group:%s is not a directory.' % (absPath, parentGroup.name))
				sys.exit(1)
			outputDir = os.path.abspath(os.path.join(absPath, outputDirName))
			if not os.path.isdir(outputDir):
				try:
					os.makedirs(outputDir)
				except Exception, e:
					Logger().error('Can not create output directory: "%s"; error:%s' % (outputDir, e))
					sys.exit(1)
			children = filter(
					lambda node: node.isaConfirmsTo('PBXGroup') and self.xcproj.absolutePathForNode(node) == outputDir and node.name == outputDirName, parentGroup.children)
			groupNode = None
			if len(children) > 1:
				Logger().warn('Duplicated output groups found, try to remove unnecessary items.')
				while len(children) > 1:
					self.xcproj.removeGroup(children[-1].guid)
				groupNode = children[0]
			elif len(children) == 1:
				groupNode = children[0]
			else:
				groupNode = addGroup(None, parentGroup.guid)
				groupNode.name = outputDirName
			self.xcproj.writeToFile()

				

	# def _prepareResourceOutfiles(self, resourceName, bundleName='main'):
	# 	outfileName = self._outfileName(resourceName, bundleName)
	# 	# headerOutfile = self._fileInProjectWithName('%s.h' % outfileName)
	# 	# sourceOutfile = self._fileInProjectWithName('%s.m' % outfileName)

	# 	# headerOutfile = headerOutfile['full_path'] if headerOutfile else None
	# 	# sourceOutfile = sourceOutfile['full_path'] if sourceOutfile else None

	# 	# if not headerOutfile:
	# 	# 	headerOutfile = 'auto_gen/%s.h' % outfileName
	# 	# if not sourceOutfile:
	# 	# 	sourceOutfile = 'auto_gen/%s.m' % outfileName

	# 	# outpath = os.path.dirname(os.path.join(self.xcproj.projectHome, headerOutfile))
	# 	# if not os.path.isdir(outpath):
	# 	# 	os.makedirs(outpath)
	# 	# outpath = os.path.dirname(os.path.join(self.xcproj.projectHome, sourceOutfile))
	# 	# if not os.path.isdir(outpath):
	# 	# 	os.makedirs(outpath)
	# 	# return headerOutfile, sourceOutfile

	def _outfileName(self, resourceName='', bundleName='main'):
		if len(bundleName) == 0:
			bundleName = 'main'
		if resourceName == '':
			return 'AppResources' if bundleName.lower() == 'main' else '%s.Resources' % bundleName.title()

		return '%s.%s' % (bundleName.title(), resourceName.title())

	# def _fileInProjectWithName(self, name):
	# 	objs = self.xcproj.getfiles(args={'path': name})
	# 	return objs[0] if len(objs) > 0 else None


if __name__ == "__main__":
	Logger().verbose('executable file: %s' % __file__)
	projPath = '/Users/baidu/workspace/testing/netdisk/netdisk/netdisk_iphone/netdisk_iPhone.xcodeproj'
	xcproj = utils.pbxprojParser.XCProject(projPath)
	ImagesResourceBuilder(xcproj)._propertiesOfClass('Res_Imagesets', '/Users/baidu/workspace/testing/netdisk/netdisk/netdisk_iphone/auto_gen/Res_Imagesets.h')
	# out = utils.functions.trimComment('/Users/baidu/workspace/Baidu/netdisk/netdisk/netdisk_iphone/netdisk_iPhone/AppDelegate.h')
	# lines = out.splitlines()
	# print lines
