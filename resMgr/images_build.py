#!/usr/bin/python
#encoding:utf-8
#Filename: images_build.py

import os
import sys
import json

root=os.path.join(os.path.dirname(__file__), "..")
if not root in sys.path:
	sys.path.append(root)

import utils

##################################################################################################
class ImagesResource(object):
	""" images resource base operations """
	def __init__(self, xcodeproj):
		super(ImagesResource, self).__init__()
		self.xcodeproj = xcodeproj

	def allImageResource(self):
		imagesets = self.imagesets()
		imageFiles = self.imageFiles()


	def imagesets(self, ignoreAssetsGroups=()):
		assets = []
		for f in [f for f in self.xcodeproj.getfiles() if str(self.xcodeproj.childrenWithKeyPathAtNode(['lastKnownFileType'], f)) == 'folder.assetcatalog']:
			if f in ignoreAssetsGroups:
				utils.Logger().warn('Ignore xcassets: %s' % f['path'])
				continue
			self.loadAssetsFromPath(f['full_path'], assets)

		imageAssets = {}
		duplicatedImages = {}
		for asset in sorted(assets, key=lambda x:x['name']):
			if imageAssets.has_key(asset['name']):
				if duplicatedImages.has_key(asset['name']):
					duplicatedImages[asset['name']].append(asset['full_path'])
				else:
					duplicatedImages[asset['name']] = [asset['full_path']]
			else:
				imageAssets[asset['name']] = asset['full_path']
		if len(duplicatedImages) > 0:
			errmsg = 'Duplicated image names found:'
			for name in duplicatedImages.keys():
				errmsg = errmsg + '\n' + name + '=>\n' + '\n'.join(['%s' % t for t in duplicatedImages[name]]) + '\n'
			utils.Logger().error(errmsg)
			sys.exit(1)

		return imageAssets


	def loadAssetsFromPath(self, assetPath, assets):
		abspath = os.path.abspath(os.path.join(self.xcodeproj.projectHome, assetPath));
		for f in [f for f in os.listdir(abspath) if os.path.isdir(os.path.join(abspath, f))]:
			if f[-(len('.imageset')):] == '.imageset':
				imgset = f.lower()
				abspath = os.path.join(abspath, f);
				contentJson = os.path.join(abspath, 'Contents.json');
				if os.path.exists(contentJson):
					fp = open(contentJson)
					contents = fp.read()
					fp.close()
					contents = json.loads(contents)
					if contents.has_key('images'):
						for image in [f['filename'] for f in contents['images'] if f.has_key('filename')]:
							if not os.path.isfile(os.path.join(abspath, image)):
								utils.Logger().warn('image file:"%s" not found in imageset:"%s"' % (image, abspath[len(self.xcodeproj.projectHome) + 1:]))
						
						assets.append({'name': imgset, 'full_path': abspath[len(self.xcodeproj.projectHome) + 1:]})
			else:
				self.loadAssetsFromPath(os.path.join(assetPath, f), assets)




	def imageFiles(self, ignoreGroupPaths=('External_Libraries_and_Frameworks')):
		imageResources = {}
		duplicatedImages = {}
		for f in [f for f in self.xcodeproj.getfiles() if str(self.xcodeproj.objectWithKeyPath(['lastKnownFileType'], f))[0:6] == 'image.']:
			shouldIgnore = False
			for ig in ignoreGroupPaths:
				if self.isParentFolder(ig, f['groups']):
					shouldIgnore = True
					break
			if shouldIgnore:
				utils.Logger().warn('Ignore file:%s' % f['full_path'])
				continue

			imgName = self.imageNameFromPath(os.path.basename(f['path'])).lower()
			is9PatchImage = False
			if imgName[-2:] == '.9':
				is9PatchImage = True
				imgName = imgName[0:-2]

			if imageResources.has_key(imgName) and os.path.basename(f['path']).lower() in [os.path.basename(fn['path']).lower() for fn in imageResources[imgName]]:
				if not duplicatedImages.has_key(imgName):
					duplicatedImages[imgName] = []
				duplicatedImages[imgName].append(f['full_path'])
			else:
				if not imageResources.has_key(imgName):
					imageResources[imgName] = {'files':[], 'is9PatchImage':is9PatchImage}
				imageResources[imgName]['files'].append(f['full_path'])

		if len(duplicatedImages) > 0:
			errmsg = 'Duplicated image names found:'
			for name in duplicatedImages.keys():
				errmsg = errmsg + '\n' + '\n'.join(['%s' % t for t in duplicatedImages[name]]) + '\n'
			utils.Logger().error(errmsg)
			sys.exit(1)

		notFoundImages = []
		for arr in imageResources.values():
			for f in arr:
				imagepath = os.path.join(self.xcodeproj.projectHome, f['full_path'])
				if not os.path.isfile(imagepath):
					notFoundImages.append(f['full_path'])
		if len(notFoundImages) > 0:
			errmsg = 'Image files not found:\n' + '\n'.join('%s' % f for f in notFoundImages) + '\n'
			utils.Logger().error(errmsg)
			sys.exit(1)

		return imageResources
	## end of "def loadImagesResource()"		




	## end of "def imageNameFromPath()"


	def isParentFolder(self, parent, child):
		if not parent or not child:
			return False

		parent = os.path.normpath(parent)
		child = os.path.normpath(child)

		if parent == child:
			return True

		if len(parent) < len(child):
			parent = parent + '/'
			if child[0:len(parent)] == parent:
				return True

		return False
	## end of "def isParentFolder()"

##################################################################################################
class ImagesResourceBuilder(object):
	def __init__(self, xcproj):
		super(ImagesResourceBuilder, self).__init__()
		self.xcproj = xcproj

	def setOutputFile(self, filePath):
		if not os.path.dirname(filePath) == self.xcproj.projectHome:
			utils.Logger().error('"%s" not in project directory' % filePath)
		self.outfile = filePath

	def loadPreviousResource(self):
		pass



if __name__=="__main__":
	projPath = '/Users/baidu/workspace/test/netdisk_iphone/netdisk_iPhone.xcodeproj'
	xcproj = utils.pbxprojParser.XCProject(projPath)
	for node in  xcproj.getfiles({'isa':'PBXFileReference', 'lastKnownFileType':'folder.assetcatalog', 'sourceTree':'<group>'}):
		utils.Logger().info('%s' % node['path'])

	imgRes = ImagesResource(xcproj)
	for k, v in imgRes.loadImageXCAssets().items():
		utils.Logger().info('%s\t=> %s' % (k, v))


