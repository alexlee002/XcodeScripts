#!/usr/bin/python
#encoding:utf-8
#Filename: xcassets_gen.py

#http://effbot.org/downloads/Imaging-1.1.7.tar.gz

import sys
import os

root=os.path.join(os.path.dirname(__file__), "..")
if not root in sys.path:
	sys.path.append(root)
import utils
import subprocess


## Check dependence of PIL, we need this module to process images
ImageModuleName = "Image"
try:
	__import__(ImageModuleName)
except Exception, e:
	utils.Logger().warn('Module "%s" is not installed, try to install it automatically ...' % ImageModuleName)
	easy_install = utils.pathForCmd('easy_install')
	if easy_install == None:
		utils.Logger().error('Automatic installation can not be completed, please install %s manually.' % ImageModuleName)
		sys.exit(1)

	p = subprocess.Popen(['sudo', easy_install, 'PIL'],stdout=subprocess.PIPE)
	stdout,stderr = p.communicate()
	if p.returncode != 0:
		if stderr:
			utils.Logger().verbose(stderr)
		utils.Logger().error('Automatic installation can not be completed, please install %s manually.' % ImageModuleName)
		utils.Logger().info('If installation failed caused by "\'X11/Xlib.h\' file not found", Please try to run "xcode-select --install" to install Xcode command-line tools first and then try again.')
		sys.exit(1)

	utils.Logger().info('========= Install %s completed ========' % ImageModuleName)

## END of checking dependence for PIL 


import json
import shutil
import glob

class XCAssetsGen(object):
	""" create imagesets automatically and add to XCAssets """
	def __init__(self, imagesPath, xcassetPath):
		super(XCAssetsGen, self).__init__()
		self.imagesPath = os.path.abspath(imagesPath)
		self.xcassetPath = os.path.abspath(xcassetPath)

	# copy images to imagesets
	#mergeMode:
	#	MERGE: use new file to replace the old one
	#	IGNORE: keep the old file and ignore the new file
	#	OVERWRITE: clear the imageset directory and use new files to build a new imageset
	def makeImagesets(self, mergeMode=utils.MergeMode.MERGE):
		self.images = {}
		self.conflicts = {}
		self.needConfirm = {}
		self._loadImages(self.imagesPath)
		if len(self.conflicts) > 0:
			errMsg = 'Conflicts found:\n\n'
			for imageName in self.conflicts.keys():
				errMsg = errMsg + '\n' + imageName + ' =>\n' + '\n'.join(t for t in self.conflicts[imageName]) + '\n'
			utils.Logger().error(errMsg)
			sys.exit(1)
		if len(self.needConfirm) > 0:
			errMsg = 'Images have same but not in the same directory, please make sure if there are the same imageset and put them in the same directory:\n\n'
			for imageName in self.needConfirm.keys():
				errMsg = errMsg + '\n' + imageName + ' =>\n' + '\n'.join(t for t in self.needConfirm[imageName]) + '\n'
			utils.Logger().error(errMsg)
			sys.exit(1)

		if not os.path.isdir(self.xcassetPath) and not os.makedirs(self.xcassetPath):
			utils.Logger().error('Can not create directory:"%s"' % self.xcassetPath)
			sys.exit(1)
		for imageName, imageArray in self.images.items():
			abspath = imageArray[0][1]
			imgPath = abspath[(len(self.imagesPath) + 1) :]
			imagesetPath = os.path.join(os.path.dirname(imgPath), imageName + '.imageset')
			destPath = os.path.join(self.xcassetPath, imagesetPath)
			if mergeMode == utils.MergeMode.OVERWRITE:
				shutil.rmtree(destPath)
			if not os.path.isdir(destPath) and not os.makedirs(destPath):
				utils.Logger().error('Can not create directory:"%s"' % destPath)
				sys.exit(1)

			try:
				for attrs, path in imageArray:
					(name, sliceImage, scale, idiom) = attrs
					destName = self._completeFileNameWithAttributes(imageAttrs, imageName, os.path.splitext(path)[1])
					destFilePath = os.path.join(destPath, destName)
					if not mergeMode == utils.MergeMode.IGNORE:
						oldFile = self._completeFileNameWithAttributes(('*', sliceImage, scale, idiom), '*', '*')
						for oldFile in glob.glob(os.path.join(destPath, oldFile)):
							os.remove(oldFile)
						shutil.copyfile(path, destFilePath)
					elif not os.path.isfile(destFilePath):
						shutil.copyfile(path, destFilePath)
			except Exception, e:
				utils.Logger().error(e)
				sys.exit(1)
		return self

	def buildImagesets(self):
		if not os.path.isdir(self.xcassetPath) and not os.path.splitext(self.xcassetPath)[1] == '.xcassets':
			utils.Logger().error('directory:"%s" is not a valid xcassets path')
			sys.exit(1)

		def _builder():
			for f in os.listdir(self.xcassetPath):
				abspath = os.path.join(self.xcassetPath, f)
				if os.path.isdir(abspath) and os.path.splitext(abspath)[1] == '.imageset':
					needUpdate = False
					jsonfile = os.path.join(abspath, 'Contents.json')
					if not os.path.isfile(json):
						needUpdate = True
					else:
						resMTime = os.stat(abspath).st_mtime
						jsonfileMTime = os.stat(jsonfile).st_mtime
						if not resMTime == jsonfileMTime:
							needUpdate = True
					#if needUpdate:

		#_builder()




	def _buildImageset(self, imagesetPath):
		contents = {}
		jsonfile = os.path.join(imagesetPath, 'Contents.json')
		if os.path.isfile(jsonfile):
			with open(jsonfile) as jsonString
			contents = json.loads(jsonString)

		def _keyValuePairsEquals(dic1, dic2, keys):
			for key in keys:
				if dic1.has_key(key) and dic2.has_key(key) and dic1[key] == dic2[key]:
					return True
			return False

		def _findImageObjectEquals(array, imageObj):
			for srcObj in array:
				if _keyValuePairsEquals(srcObj, imageObj, ('idiom', 'scale')) and srcObj.has_key('filename') && imageObj.has_key('filename') and srcObj['filename'] != imageObj['filename']:
					return srcObj
			return None

		def _buildContentsJson(images, ):

			

		images = []
		imageFiles = [f for f in os.listdir(imagesetPath) if self._isImageFile(os.path.join(imagesetPath, f))]
		hasConflict = False
		for f in imageFiles:
			imageName, sliceImage, scale, idiom = utils.parseImageFileName(f)
			imageObj = {'idiom':idiom, 'scale':scale, 'filename':f}
			conflictObj = _findImageObjectEquals(images, imageObj)
			if conflictObj:
				utils.appendObjectToDicForKey(self.conflicts, imagesetPath, imageObj)
				utils.appendObjectToDicForKey(self.conflicts, imagesetPath, conflictObj)
				hasConflict = True
			else:
				images.append(imageObj)

		if not hasConflict:
			_buildContentsJson(images)



		





	def _loadImages(self, path, deepth=0):
		if deepth > 5:
			utils.Logger().error('Recursive deepth is too big')
			return
		if os.path.isdir(path) and os.path.splitext(path)[1] == '.imageset':
			self._checkConflict(None, path, True)

		for f in os.listdir(path):
			abspath = os.path.join(abspath, f)
			if self._isImageFile(abspath):
				self._checkConflict(utils.parseImageFileName(f), abspath)
			elif os.path.isdir(abspath):
				self._loadImages(abspath, deepth + 1)

	def _isImageFile(self, filepath):
		if not os.path.isfile(filepath):
			return False

		defaultImageExts = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp')
		fileCmd = utils.pathForCmd('file')
		if not fileCmd == None:
			p = subprocess.Popen([fileCmd, filepath], stdout=subprocess.PIPE)
			stdout,stderr = p.communicate()
			if p.returncode == 0:
				return stdout.split('\n')[0].find(' image data, ') > 0
		return os.path.splitext(filepath)[1].lower() in defaultImageExts

	def _checkConflict(self, imageAttrs, path, imagesets=False):
		if imagesets:
			imageName = os.path.splitext(os.path.basename(path))[0]
			if self.images.has_key(imageName):
				utils.appendObjectToDicForKey(self.conflicts, imageName, path)
				return
			attrs = []
			_tmpImages = []
			hasConflict = False
			for f in [f for f in os.listdir(path) if self._isImageFile(os.path.join(path, f))]:
				imgAttrs = utils.parseImageFileName(f)
				for attr in attrs:
					if attr == imgAttrs[1:]:
						utils.appendObjectToDicForKey(self.conflicts, imageName, os.path.join(path, f))
						hasConflict = True
					else:
						_tmpImages.append(((imageName, imgAttrs[1], imgAttrs[2], imgAttrs[3]), os.path.join(path, f)))
					attrs.append(imgAttrs[1:])
			if not hasConflict:
				utils.appendObjectToDicForKey(self.images, imageName, _tmpImages)
			return #end of "if imagesets:"

		imageName = imageAttrs[0]
		if self.images.has_key(imageName):
			for fileObj in self.images[imageName]:
				fileObjAttrs = fileObj[0]
				fileObjPath = fileObj[1]
				if imageAttrs == fileObjAttrs:
					utils.appendObjectToDicForKey(self.conflicts, imageName, path)
				elif not os.path.dirname(path) == os.path.dirname(fileObjPath):
					utils.appendObjectToDicForKey(self.needConfirm, imageName, path)
				else:
					utils.appendObjectToDicForKey(self.images, imageName, (imageAttrs, path))


	def _completeFileNameWithAttributes(self, attributes, imageName=None, nameExt='.png'):
		name, sliceImage, scale, device = attributes
		if imageName:
			destName = imageName
		else:
			destName = name
		if sliceImage:
			destName = destName + '.9'
		if not scale == 1:
			destName = '%s@%s' % (destName, scale)
		if not device == utils.DeviceType.UNIVERSAL:
			destName = '%s~%s' % (destName, device)
		if nameExt:
			destName = destName + nameExt
		else:
			destName = destName + '.png'
		return destName






if __name__ == '__main__':
	gen = XCAssetsGen('/Users/baidu/Downloads/', '/Users/baidu/Downloads/a.xcassets')
	#print gen._completeFileNameWithAttributes(('abc.bj', False, 1, '~ipad'), 'abc_bj', '.jpg')
	gen.buildImagesets()
