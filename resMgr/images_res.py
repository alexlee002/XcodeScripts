#!/usr/bin/python
#encoding:utf-8
#Filename: images_res.py

import os
import sys

mymoduleRoot = os.path.join(os.path.dirname(__file__), "..")
if not mymoduleRoot in sys.path:
	sys.path.append(mymoduleRoot)

from utils.functions import *
from utils.logger import Logger
from pbxproj.pbxnode import *
from pbxproj.pbxproj import *


class Imageset(object):
	"""docstring for Imageset"""
	def __init__(self, path, xcassets=None):
		super(Imageset, self).__init__()
		self.path = path
		self.xcassets = xcassets
		self.name = None

	def imageName(self):
		if self.name is None and self.path:
			name = os.path.basename(self.path)
			name, ext = os.path.splitext(name)
			if ext.lower() == '.imageset':
				self.name = name
		return self.name


class ImagesResource(object):
	def __init__(self, xcproj):
		super(ImagesResource, self).__init__()
		self.xcproj = xcproj

	def imageFiles(self, targetName):
		imageObjects = {}
		conflicts = {}
		resourcePhase = self._resourcePhase(targetName)
		if resourcePhase:
			for buildFileId in resourcePhase.files:
				node = self.xcproj.nodeWithGuid(buildFileId)
				if node and node.isaConfirmsTo('PBXBuildFile'):
					node = self.xcproj.nodeWithGuid(node.fileRef)
					if node and node.isaConfirmsTo('PBXFileReference') and stringHasPrefix(node.fileType(), 'image.', ignoreCase=True):
						self._addImageObject(self._pathForImage(node), node.name, imageObjects, conflicts)

					elif node and node.isaConfirmsTo('PBXVariantGroup') and len(node.children) > 0:
						child = self.xcproj.nodeWithGuid(node.children[0])
						if child.isaConfirmsTo('PBXFileReference') and stringHasPrefix(child.fileType(), 'image.', ignoreCase=True):
							self._addImageObject(self._pathForImage(node), node.name, imageObjects, conflicts)
		return imageObjects, conflicts

	def imagesets(self, targetName):
		imagesets = {}
		conflicts = {}

		def _imagesetsFromPath(path):
			if os.path.isdir(path):
				for f in filter(lambda f: os.path.isdir(os.path.join(path, f)), os.listdir(path)):
					pathName, pathExt = os.path.splitext(f)
					pathExt = pathExt.lower()
					if pathExt == '.imageset':
						imgset = Imageset(os.path.join(path, f))
						self._addImageObject(self._pathForImage(imgset), imgset.imageName(), imagesets, conflicts)
					elif not pathExt in ('.launchimage', '.appiconset'):
						_imagesetsFromPath(os.path.join(path, f))

		resourcePhase = self._resourcePhase(targetName)
		if not resourcePhase:
			return {}
		for buildFileId in resourcePhase.files:
			node = self.xcproj.nodeWithGuid(buildFileId)
			if node and node.isaConfirmsTo('PBXBuildFile'):
				node = self.xcproj.nodeWithGuid(node.fileRef)
				if node and node.isaConfirmsTo('PBXFileReference') \
					and node.fileType() == 'folder.assetcatalog' \
					and stringHasSubfix(node.path, '.xcassets', ignoreCase=True):
					xcassetsPath = self.xcproj.absolutePathForNode(node.guid)
					_imagesetsFromPath(xcassetsPath)
		return imagesets, conflicts

	def _resourcePhase(self, targetName):
		target = self.xcproj.targetNamed(targetName)
		if not target:
			Logger().error('target "%s" not found in project "%s".' % (targetName, self.xcproj.projectHome))
			sys.exit(1)
		resourcePhase = None
		for buildPhaseId in target.buildPhases:
			buildPhase = self.xcproj.nodeWithGuid(buildPhaseId)
			if buildPhase and buildPhase.isaConfirmsTo('PBXResourcesBuildPhase'):
				resourcePhase = buildPhase
				break
		return resourcePhase

	def _addImageObject(self, imgPath, name, imagesDict, conflictsDict):
		from xcassets import ImageModel
		canonicalName = ImageModel.canonicalImageNameWitName(name)
		if not canonicalName:
			Logger().error('image name is illegal, image name must matches "^[\w_][\w\d_]+$"')
			sys.exit(1)
		if canonicalName.lower() in map(lambda k: k.lower(), imagesDict.keys()):
			if canonicalName in conflictsDict:
				conflictsDict[canonicalName].append(imgPath)
			else:
				conflictsDict[canonicalName] = [imgPath]
		else:
			imagesDict[canonicalName] = imgPath

	def _pathForImage(self, imgObj):
		if isinstance(imgObj, PBXNode):
			path = self.xcproj.absolutePathForNode(imgObj.guid)
		if isinstance(imgObj, Imageset):
			path = imgObj.path
		if isSubPathOf(path, self.xcproj.projectHome):
			path = path[len(self.xcproj.projectHome)+1:]
		return path


#######################################################################################
def Test_loadImagesets():
	xcproj = XcodeProject().parseXcodeProject('/Users/baidu/workspace/testing/netdisk/netdisk/netdisk_iphone/netdisk_iPhone.xcodeproj')
	imagesets, confilcts = ImagesResource(xcproj).imagesets(targetName='netdisk_iPhone')
	print '-------------- imagesets --------------'
	for name, path in imagesets.items():
		print '\t%s\t\t=> %s' % (name, path)
	print '-------------- confilcts --------------'
	for name, path in confilcts.items():
		print '\t%s\t\t=> %s' % (name, path)


def main():
	Test_loadImagesets()

if __name__ == '__main__':
	main()
