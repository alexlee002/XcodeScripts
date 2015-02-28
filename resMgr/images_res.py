#!/usr/bin/python
#encoding:utf-8
#Filename: images_res.py

import os
import sys
import json

mymoduleRoot = os.path.join(os.path.dirname(__file__), "..")
if not mymoduleRoot in sys.path:
	sys.path.append(mymoduleRoot)

import utils
import utils.functions


class ImagesResource(object):
	def __init__(self, xcproj):
		super(ImagesResource, self).__init__()
		self.xcproj = xcproj

	def allImageObjects(self):
		imageFiles = self.loadImages()
		imagesets = self.loadImagesets()
		duplicatedImages = {}
		for name, files in imageFiles.items():
			if name in imagesets:
				duplicatedImages[name] = (files[0], imagesets[name])
		if len(duplicatedImages) > 0:
			self._exitWithImageNamesConflictMessage(duplicatedImages)
		return imageFiles, imagesets

	# load images which is directly added to the project/boundles, not in imagesets
	def loadImages(self, ignoreGroupPaths=()):
		from xcassets import ImageModel
		imageResources = {}
		duplicatedImages = {}

		for f in [f for f in self.xcproj.getfiles() if str(self.xcproj.childrenWithKeyPathAtNode(('lastKnownFileType',), f))[0:6] == 'image.']:
			shouldIgnore = False
			for ig in ignoreGroupPaths:
				if utils.isSubPathOf(path=f['groups'], ancestor=ig):
					shouldIgnore = True
					break
			if shouldIgnore:
				utils.logger.Logger().verbose('Ignore file:%s' % f['full_path'])
				continue

			imagePath = (os.path.basename(f['path'])).lower()
			(imgName, scale, idiom, ext, sliceImage, subtype) = ImageModel.parseImageFileName(imagePath)
			#check duplicate images
			#TODO: need to support localizad images, and bundle-inside images
			if imgName in imageResources:
				for imgObj in imageResources[imgName]:
					if (imgName, scale, idiom, subtype) == imgObj[1]:
						if imgName not in duplicatedImages:
							duplicatedImages[imgName] = [imgObj[0]]
						duplicatedImages[imgName].append(f['full_path'])
						break
			else:
				if imgName not in imageResources:
					imageResources[imgName] = []
				imageResources[imgName].append((f['full_path'], (imgName, scale, idiom, subtype)))

		if len(duplicatedImages) > 0:
			self._exitWithImageNamesConflictMessage(duplicatedImages)

		notFoundImages = []
		images = {}
		for imgName, arr in imageResources.items():
			files = []
			for f in arr:
				files.append(f[0])
				imagepath = os.path.join(self.xcproj.projectHome, f[0])
				if not os.path.isfile(imagepath):
					notFoundImages.append(f[0])
			images[imgName] = files

		if len(notFoundImages) > 0:
			errmsg = 'Image files not found:\n' + '\n'.join('%s' % f for f in notFoundImages) + '\n'
			utils.logger.Logger().error(errmsg)
			sys.exit(1)

		return images

	def loadImagesets(self, ignoreAssets=()):
		assets = []

		def __loadImagesetsFromAssets(assetPath):
			from xcassets import ImageModel
			abspath = os.path.abspath(os.path.join(self.xcproj.projectHome, assetPath))
			for f in [f for f in os.listdir(abspath) if os.path.isdir(os.path.join(abspath, f))]:
				if utils.functions.stringHasSubfix(f, subfix='.imageset'):
					imgset = os.path.splitext(f)[0].lower()
					imgset = ImageModel.canonicalImageNameWitName(imgset)
					imgsetPath = os.path.join(abspath, f)
					contentJson = os.path.join(imgsetPath, 'Contents.json')
					if os.path.exists(contentJson):
						with open(contentJson) as fp:
							contents = fp.read()
						contents = json.loads(contents)
						if 'images' in contents:
							#for image in [f['filename'] for f in contents['images'] if 'filename' in f]:
								#if not os.path.isfile(os.path.join(imgsetPath, image)):
									#utils.logger.Logger().warn('image file:"%s" not found in imageset:"%s"' % (image, imgsetPath[len(self.xcproj.projectHome) + 1:]))
							assets.append({'name':  imgset, 'full_path': imgsetPath[len(self.xcproj.projectHome) + 1:]})
				elif not utils.functions.stringHasSubfix(f, subfix='.appiconset') and not utils.functions.stringHasSubfix(f, subfix='.launchimage'):
					__loadImagesetsFromAssets(os.path.join(assetPath, f))
		#end of __loadImagesetsFromAssets

		for f in [f for f in self.xcproj.getfiles() if str(self.xcproj.childrenWithKeyPathAtNode(['lastKnownFileType'], f)) == 'folder.assetcatalog']:
			if f in ignoreAssets:
				utils.logger.Logger().verbose('Ignore xcassets: %s' % f['path'])
				continue
			__loadImagesetsFromAssets(f['full_path'])

		imageAssets = {}
		duplicatedImages = {}
		for asset in sorted(assets, key=lambda x: x['name']):
			if asset['name'] in imageAssets:
				if asset['name'] in duplicatedImages:
					duplicatedImages[asset['name']].append(asset['full_path'])
				else:
					duplicatedImages[asset['name']] = [asset['full_path']]
			else:
				imageAssets[asset['name']] = asset['full_path']
		if len(duplicatedImages) > 0:
			self._exitWithImageNamesConflictMessage(duplicatedImages)

		return imageAssets

	def _exitWithImageNamesConflictMessage(self, conflicts):
		errmsg = 'Image names conflict:'
		for name in conflicts.keys():
			errmsg = errmsg + '\n' + name + '=>\n' + '\n'.join(['%s' % t for t in conflicts[name]]) + '\n'
		utils.logger.Logger().error(errmsg)
		sys.exit(1)


if __name__ == '__main__':
	print __file__ + ':' + ('YES' if utils.functions.stringHasSubfix('abc.imageset', '.imageset') else 'NO')
