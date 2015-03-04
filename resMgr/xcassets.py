#!/usr/bin/python
#encoding:utf-8
#Filename: xcassets.py


import sys
import os
import json
import shutil
import glob
import subprocess
import re

import urllib
# from urllib import urlencode
# from urllib import unquote
# from var_dump import var_dump

myModulePath = os.path.join(os.path.dirname(__file__), "..")
if not myModulePath in sys.path:
	sys.path.append(myModulePath)

import utils
from utils.logger import Logger
from utils.constants import MergeMode
from utils.constants import IdiomType
from utils.functions import __line__

# constant vars
DefaultImageResizingMode = 'fill'
DefaultContentsJsonVersion = 1
DefaultContentsJsonAuthor = 'xcode'

NinePatchImageBorderBGColors = ((0, 0, 0, 0), (255, 255, 255, 255), (255, 255, 255, 0))
NinePatchImageBorderMarkerColor = (0, 0, 0, 255)

SupportIdioms = (IdiomType.IPHONE, IdiomType.IPAD, IdiomType.UNIVERSAL)
SupportedScale = ('1x', '2x', '3x')

ImageModuleName = 'Image'


def checkMoulePIL():
	## Check dependence of PIL, we need this module to process images
	try:
		__import__(ImageModuleName)
	except Exception:
		Logger().warn(
			'Python Module "%s" (PIL) is not installed, '
			'and it is required to parse resizing-images. try to install it automatically ...' % ImageModuleName)
		easy_install = utils.functions.pathForShell('easy_install')
		if easy_install is None:
			Logger().error('Command: "easy_install" is not found, auto-installation is not complete, please install %s (PIL) manually.' % ImageModuleName)
			sys.exit(1)

		p = subprocess.Popen(['sudo', easy_install, 'PIL'], stdout=subprocess.PIPE)
		stdout, stderr = p.communicate()
		if p.returncode != 0:
			if stderr:
				Logger().verbose(stderr)
			if stdout:
				Logger().verbose(stdout)
			Logger().error('Auto-installation is not completed, please install %s (PIL) manually.' % ImageModuleName)
			Logger().info(
				'If installation failed caused by "\'X11/Xlib.h\' file not found", '
				'Please try to run "xcode-select --install" to install Xcode command-line tools'
				' and then try again.')
			sys.exit(1)

		Logger().info('========= Install PIL completed ========')
	## END of checking dependence for PIL


class ImageModel(object):
	def __init__(self, filePath, attributes=None):
		super(ImageModel, self).__init__()
		assignedName = filePath if filePath is not None else attributes[0]
		self.name = self.scale = self.idiom = self.ext = self.sliceImage = self.subtype = None
		self.filePath = filePath
		if filePath:
			attributes = ImageModel.parseImageFileName(filePath)
		if attributes and len(attributes) == 6:
			self.name, self.scale, self.idiom, self.ext, self.sliceImage, self.subtype = attributes

		if self.name:
			self.name = ImageModel.canonicalImageNameWitName(self.name)
		if self.name is None and assignedName is not None:
			import traceback
			Logger().error('Illegal file name: %s, allow characters:[a-zA-Z0-9_.]' % filePath)
			traceback.print_stack()
			sys.exit(1)
		self.resizing = None  # dict
		self.needRewriteSliceImage = False
		#print 'attrs: %s' % attributes

	def __str__(self):
		return str(self.toDict())

	def __repr__(self):
		return repr(self.toDict())

	def toDict(self):
		dic = {}
		if self.idiom:
			dic['idiom'] = self.idiom
		if self.name:
			dic['filename'] = self.canonicalFileName()
		if self.scale:
			dic['scale'] = self.scale
		if self.subtype == '-568h':
			dic['subtype'] = 'retina4'
		if self.resizing:
			dic['resizing'] = self.resizing
		return dic

	def equalsTo(self, other, ignoreName=False):
		if not type(other) is ImageModel:
			return False
		if self.scale == other.scale and self.idiom == other.scale and self.subtype == other.subtype:
			if ignoreName:
				return True
			return self.name == other.name
		return False

	@staticmethod
	def parseImageFileName(fileName):
		if not fileName:
			return None
		name = None
		sliceImage = False
		scale = '1x'
		idiom = IdiomType.UNIVERSAL
		subtype = None
		ext = 'png'

		fileName = os.path.basename(fileName)
		name, ext = os.path.splitext(fileName)

		subfixPattern = '(\.9)?(\-\d+h)?(@(\dx))?(~(ipad|iphone))?(\.png|\.jpg)'
		m = re.search(subfixPattern, fileName, re.IGNORECASE)
		if m and m.group():
			subfixs = m.group()
		if fileName[-len(subfixs):] == subfixs:
			name = fileName[:-len(subfixs)]
			(nine_patch, subtype, scaleStr, scale, idiomStr, idiom, ext) = m.groups()
			if nine_patch and nine_patch == '.9':
				sliceImage = True
			if not scale or not scale in SupportedScale:
				scale = '1x'
			if not idiom or not idiom in SupportIdioms:
				idiom = IdiomType.UNIVERSAL
		#filter special chars
		return (name, scale, idiom, ext, sliceImage, subtype)

	@staticmethod
	def canonicalImageNameWitName(name):
		name = urllib.unquote(name)
		name = re.sub('[^\w\d_]', '_', name)
		while name.find('__') > 0:
			name = name.replace('__', '_')
		name = None if name == '_' else name
		return name

	@staticmethod
	def imageModeFromDict(dic):
		model = ImageModel(None)
		(model.idiom, fn, model.scale, model.subtype, model.resizing) = utils.functions.valueOrNoneFromDictWithKeys(
			dic,
			('idiom', 'filename', 'scale', 'subtype', 'resizing'))
		(model.name, s, i, model.ext, model.sliceImage, t) = ImageModel.parseImageFileName(fn)
		model.name = ImageModel.canonicalImageNameWitName(model.name)
		if model.name is None and fn is not None:
			Logger().error('Illegal file name: %s, allow characters:[a-zA-Z0-9_.]' % fn)
			sys.exit(1)
		return model

	@staticmethod
	def fileNameWithAttributes(attributes):
		(name, scale, idiom, ext, sliceImage, subtype) = attributes
		destName = ''
		if name:
			destName = name
		if sliceImage:
			destName += '.9'
		if subtype:
			destName += subtype
		if scale and not scale == '1x':
			destName += '@%s' % scale
		if idiom and not idiom == IdiomType.UNIVERSAL:
			destName += '~%s' % idiom
		if ext:
			destName += ext
		else:
			destName += '.png'
		return destName

	def canonicalFileName(self):
		return ImageModel.fileNameWithAttributes((self.name, self.scale, self.idiom, self.ext, self.sliceImage, self.subtype))


#########################################################################################################
class XCAssets(object):
	""" build or check configuration for xcode assets """
	def __init__(self, xcassetPath):
		super(XCAssets, self).__init__()
		if not os.path.splitext(xcassetPath)[1] == '.xcassets':
			xcassetPath = os.path.join(xcassetPath, 'Images.xcassets')
		self.xcassetPath = xcassetPath

	# copy images to imagesets
	#mergeMode:
	#	MERGE: use new file to replace the old one
	#	IGNORE: keep the old file and ignore the new file
	#	OVERWRITE: clear the imageset directory and use new files to build a new imageset
	def makeImagesets(self, imagesPath, mergeMode=MergeMode.MERGE):
		images = {}
		conflicts = {}

		#inner function
		def _verifyImageFile(abspath):
			newImg = ImageModel(abspath)
			if newImg.name in images:
				hasConflict = False
				for oldImg in images[newImg.name]:
					if newImg.filePath and oldImg.filePath and not os.path.dirname(newImg.filePath) == os.path.dirname(oldImg.filePath):
						hasConflict = True
						self._appendArrayItemToDicForKey(conflicts, newImg.name, abspath)
					if newImg.equalsTo(oldImg, ignoreName=True):
						hasConflict = True
						self._appendArrayItemToDicForKey(conflicts, newImg.name, abspath)

				if not hasConflict:
					self._appendArrayItemToDicForKey(images, newImg.name, newImg)
			else:
				self._appendArrayItemToDicForKey(images, newImg.name, newImg)

		#inner function
		def _loadImages(path, deepth=0):
			if deepth > 5:
				Logger().warn('Recursive count exceed.(%s:%s)' % (os.path.basename(__file__), __line__))
				return

			if os.path.isdir(path) and os.path.splitext(path)[1] == '.imageset':
				self._verifyImageset(path, images, conflicts)
				return

			for f in os.listdir(path):
				abspath = os.path.join(path, f)
				Logger().verbose('loading %s ...' % abspath)
				if self._isImageFile(abspath):
					_verifyImageFile(abspath)
				elif os.path.isdir(abspath):
					_loadImages(abspath, deepth + 1)

		# logic of makeImagesets
		_loadImages(imagesPath)

		if len(conflicts) > 0:
			errMsg = 'Conflicts found:\n\n'
			for imageName in conflicts.keys():
				errMsg = errMsg + '\n' + imageName + ' =>\n' + '\n'.join(t for t in conflicts[imageName]) + '\n'
			Logger().error(errMsg)
			sys.exit(1)
		if not os.path.isdir(self.xcassetPath):
			os.makedirs(self.xcassetPath)
			if not os.path.isdir(self.xcassetPath):
				Logger().error('[1]Can not create directory:"%s"' % self.xcassetPath)
				sys.exit(1)
		for imageName, imageArray in images.items():
			abspath = imageArray[0].filePath
			imgPath = abspath[(len(imagesPath) + 1):]
			imagesetPath = os.path.join(os.path.dirname(imgPath), imageName + '.imageset')
			destPath = os.path.join(self.xcassetPath, imagesetPath)
			if mergeMode == MergeMode.OVERWRITE:
				shutil.rmtree(destPath)
			if not os.path.isdir(destPath):
				os.makedirs(destPath)
				if not os.path.isdir(destPath):
					Logger().error('[2]Can not create directory:"%s"' % destPath)
					sys.exit(1)
			try:
				for imageModel in imageArray:
					#(name, scale, idiom, ext, sliceImage, subtype) = attrs
					destName = imageModel.canonicalFileName()
					destFilePath = os.path.join(destPath, destName)
					if not mergeMode == MergeMode.IGNORE:
						#oldFile eg: :*@2x~ipad.*
						oldFile = ImageModel.fileNameWithAttributes(('*', imageModel.scale, imageModel.idiom, '.*', None, imageModel.subtype))
						for oldFile in glob.glob(os.path.join(destPath, oldFile)):
							os.remove(oldFile)
						shutil.copyfile(imageModel.filePath, destFilePath)
					elif not os.path.isfile(destFilePath):
						shutil.copyfile(imageModel.filePath, destFilePath)
			except Exception, e:
				Logger().error(e)
				sys.exit(1)
		return self
	##########################################

	def buildImagesets(self, fastMode=True, normalizeImagesetName=False):
		warnings = {}

		def _originalConfigForImageNamed(originalJson, filePath):
			fileName = os.path.basename(filePath)
			(_, scale, idiom, _, _, subtype) = ImageModel.parseImageFileName(fileName)
			if 'images' in originalJson and type(originalJson['images']) is list or type(originalJson['images']) is tuple:
				matches = []
				for imageDic in originalJson['images']:
					if 'filename' in imageDic and imageDic['filename'] == fileName:
						matches.append(imageDic)

				for imageDic in matches:
					attrs = utils.functions.valueOrNoneFromDictWithKeys(imageDic, ('scale', 'idiom', 'subtype'))
					if attrs == (scale, idiom, subtype):
						return imageDic

				if len(matches) == 1:
					return matches[0]
				elif len(matches) > 1:
					Logger().warn(
						'Conflict settings found in Original Contents.json: The same image file has multi-configs: %s; '
						'Trying to find the most matched configuration.' % filePath)
					checkMoulePIL()
					Image = __import__(ImageModuleName)
					image = Image.open(filePath)
					w, h = image.size
					for imageDic in sorted(matches.iteritems(), key=lambda d: d[1], reverse=True):
						if 'scale' in imageDic and re.match('^\d+x$', imageDic['scale']) is not None:
							intScale = int(scale[:-1])
							if w % intScale == 0 and h % intScale == 0:
								return imageDic
			return None

		def _imageFilesInOriginalConfig(originalJson):
			images = []
			if 'images' in originalJson and type(originalJson['images']) is list or type(originalJson['images']) is tuple:
				for img in originalJson['images']:
					if 'filename' in img and len(img['filename']) > 0:
						images.append(img['filename'])
			return sorted(images)

		def _updateImageModeWithOriginalConfig(originalDic, imageModel):
			if originalDic is None:
				return
			if 'scale' in originalDic and re.match('^\d+x$', originalDic['scale']) is not None:
				imageModel.scale = originalDic['scale']
			if 'idiom' in originalDic and originalDic['idiom'] in SupportIdioms:
				imageModel.idiom = originalDic['idiom']
			if 'subtype' in originalDic and originalDic['subtype'] == 'retina4':
				imageModel.subtype = '-568h'

		def _renameImageFileNameWithImagesetName(imagesetPath, imgModel):
			# rename file to canonical file name
			imageFileName = os.path.basename(imgModel.filePath)
			canonicalFileName = os.path.splitext(os.path.basename(imagesetPath))[0]
			canonicalFileName = ImageModel.canonicalImageNameWitName(canonicalFileName)
			if canonicalFileName:
				attr = (canonicalFileName, imgModel.scale, imgModel.idiom, imgModel.ext, imgModel.sliceImage, imgModel.subtype)
				canonicalFileName = ImageModel.fileNameWithAttributes(attr)
			else:
				canonicalFileName = imgModel.canonicalFileName()
			if canonicalFileName and imageFileName != canonicalFileName:
				try:
					destPath = os.path.join(imagesetPath, canonicalFileName)
					os.renames(os.path.join(imagesetPath, imageFileName), destPath)
					imgModel.name = ImageModel.parseImageFileName(canonicalFileName)[0]
					imgModel.filePath = destPath
				except Exception, e:
					imgModel.name = ImageModel.parseImageFileName(imageFileName)[0]
					Logger().warn('rename file: "%s" to "%s" failed, directory: %s; error: %s' % (imageFileName, canonicalFileName, imagesetPath, e))

		#inner function
		def _buildImageset(path):
			Logger().verbose('building imageset: "%s" ...' % path)
			originalJson = None
			jsonFile = os.path.join(path, 'Contents.json')
			if os.path.isfile(jsonFile):
				with open(jsonFile, 'rb') as fp:
					jsonString = fp.read()
					originalJson = json.loads(jsonString)

			imageFiles = sorted([f for f in os.listdir(path) if self._isImageFile(os.path.join(path, f))])

			imageDic = {}
			_addSupportedDeviceIdiom(imageDic, IdiomType.UNIVERSAL)
			hasError = False
			for f in imageFiles:
				imgModel = ImageModel(os.path.join(path, f))
				originalConfig = _originalConfigForImageNamed(originalJson, os.path.join(path, f))
				_updateImageModeWithOriginalConfig(originalConfig, imgModel)

				if imgModel.sliceImage:
					resizingImage = ResizingImage(imgModel.filePath).parseResizingImage()
					if not resizingImage:
						if originalConfig and 'resizing' in originalConfig:
							#这是一个已经处理过的9.png 图片, 保留原来 json 中的 resizing 信息
							imgModel.resizing = originalConfig['resizing']
						else:
							# 可能是一个可缩放图片, 但是丢失了resizing信息
							# 或者是一个不可缩放图片, 但是命名不规范
							# 统一按不可缩放图片处理
							Logger().warn(
								'Lost resizing information for image:"%s". '
								'This image seems to be a resizable image, '
								'but we could not find any resizing information. '
								'please check it manually.' % imgModel.filePath)
							imgModel.sliceImage = False
					else:
						imgModel.resizing = resizingImage.toDict()
						imgModel.needRewriteSliceImage = True
				## add imageModel to imageDic
				if not _addImageModelToImagesset(imageDic, imgModel, originalJson):
					hasError = True
			if not hasError:
				for k in imageDic.keys():
					imgModel = imageDic[k]
					# IMPORTANT! CAN NOT modify imgmodel attributes after _renameImageFileNameWithImagesetName()
					if imgModel.name and imgModel.filePath:
						_renameImageFileNameWithImagesetName(path, imgModel)
					if imgModel.needRewriteSliceImage:
						if not ResizingImage(imgModel.filePath).clipBorderAndOverwrite():
							Logger().warn('Failed to rewrite resizing image: "%s".' % imgModel.filePath)
				_buildJsonFile(imageDic, path)

			else:
				Logger().error('Conflicts found:')
				for k, arr in warnings.items():
					Logger().error('%s =>\n\t%s' % (k, '\n\t'.join(arr)))
					sys.exit(1)

		# def _findImageInfoFromOriginalJson(imageModel, originalJson):
		# 	if not type(originalJson) is dict or not 'images' in originalJson:
		# 		return None
		# 	for imgJson in originalJson['images']:
		# 		attrs = utils.functions.valueOrNoneFromDictWithKeys(imgJson, ('filename', 'scale', 'idiom', 'subtype'))
		# 		if attrs == (imageModel.canonicalFileName(), imageModel.scale, imageModel.idiom, imageModel.subtype):
		# 			return imgJson
		# 	return None

		def _keyForImage(imageModel):
			return '%s.%s.%s' % (imageModel.idiom, imageModel.scale, imageModel.subtype)

		def _addImageModelToImagesset(imagesDic, imageModel, originalJson):
			hasError = False
			key = _keyForImage(imageModel)
			if not key in imagesDic:
				_addSupportedDeviceIdiom(imagesDic, imageModel.idiom)
				imagesDic[key] = imageModel
			elif imagesDic[key].name is None:
				imagesDic[key] = imageModel
			else:
				imgConfig = _originalConfigForImageNamed(originalJson, imageModel.filePath)
				conflictConfig = None if imagesDic[key].filePath is None else _originalConfigForImageNamed(originalJson, imagesDic[key].filePath)

				if conflictConfig is None and imgConfig:
					imagesDic[key] = imageModel
				elif conflictConfig and imgConfig is None:
					pass
				else:
					self._appendArrayItemToDicForKey(warnings, os.path.dirname(imageModel.filePath), [imagesDic[key].canonicalFileName(), imageModel.canonicalFileName()])
					hasError = True
			return not hasError

		##
		def _buildJsonFile(imageDic, path):
			images = [img.toDict() for img in imageDic.values()]
			contents = {'images': images, 'info': {'version': DefaultContentsJsonVersion, 'author':  DefaultContentsJsonAuthor}}
			jsonFile = os.path.join(path, 'Contents.json')
			with open(jsonFile, 'wb') as fp:
				if fp:
					jstr = json.dumps(contents, sort_keys=False, indent=2)
					if jstr:
						fp.write(jstr)
					else:
						Logger().error('%s\nis not JSON serializable' % contents)
						sys.exit(1)
				else:
					Logger().error('Can not create file:%s' % jsonFile)
					sys.exit(1)

		##
		def _addSupportedDeviceIdiom(imageDic, idiom):
			hasIdiom = False
			for key in imageDic.keys():
				if key[:len(idiom)] == idiom:
					hasIdiom = True
					break
			if not hasIdiom:
				for scale in SupportedScale:
					key = '%s.%s.%s' % (idiom, scale, None)
					imageDic[key] = ImageModel(None, (None, scale, idiom, None, None, None))

		def _imagesetsBuilder(path, loops=0):
			if loops > 5:
				Logger().warn('Recursive count exceed.(%s:%s)' % (os.path.basename(__file__), __line__))
				return
			if not os.path.isdir(path):
				return

			for f in os.listdir(path):
				imagesetName, pathExt = os.path.splitext(f)
				abspath = os.path.join(path, f)
				if os.path.isdir(abspath) and pathExt == '.imageset':
					needUpdate = False

					# canonical the imageset name
					if normalizeImagesetName:
						canonicalName = ImageModel.canonicalImageNameWitName(imagesetName)
						if canonicalName and canonicalName != imagesetName:
							try:
								os.renames(abspath, os.path.join(path, ('%.imageset' % canonicalName)))
								needUpdate = True
							except Exception, e:
								Logger().warn('Normalize imageset name for imageset "%s" failed: %s' % (abspath, e))

					jsonfile = os.path.join(abspath, 'Contents.json')
					if not os.path.isfile(jsonfile) or not os.stat(abspath).st_mtime == os.stat(jsonfile).st_mtime:
						needUpdate = True
					if needUpdate or not fastMode:
						_buildImageset(abspath)

				elif not pathExt in ('.launchimage', '.appiconset'):
					_imagesetsBuilder(abspath, loops + 1)

		##
		_imagesetsBuilder(self.xcassetPath)

	##############
	def _verifyImageset(self, path, images={}, conflicts={}):
		imageName = os.path.splitext(os.path.basename(path))[0]
		if imageName in images:
			self._appendArrayItemToDicForKey(conflicts, imageName, path)
			return

		hasConflict = False
		siblings = []
		for f in os.listdir(path):
			abspath = os.path.join(path, f)
			if self._isImageFile(abspath):
				_imgModel = ImageModel(abspath)
				for sibling in siblings:
					if _imgModel.equalsTo(sibling, ignoreName=True):
						self._appendArrayItemToDicForKey(conflicts, imageName, os.path.join(path, f))
						hasConflict = True
				if not hasConflict:
					self._appendArrayItemToDicForKey(images, imageName, _imgModel)
				siblings.append(_imgModel)

	def _isImageFile(self, filepath):
		if not os.path.isfile(filepath):
			return False

		defaultImageExts = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp')
		fileCmd = utils.functions.pathForShell('file')
		if not fileCmd is None:
			p = subprocess.Popen([fileCmd, filepath], stdout=subprocess.PIPE)
			stdout, stderr = p.communicate()
			if p.returncode == 0:
				return stdout.split('\n')[0].find(' image data, ') > 0
		return os.path.splitext(filepath)[1].lower() in defaultImageExts

	def _appendArrayItemToDicForKey(self, dic, key, item):
		if key in dic:
			l = dic[key]
		else:
			l = []
			dic[key] = l

		if type(item) is list:
			l.extend(item)
		else:
			l.append(item)


class ResizingImage(object):
	"""docstring for ResizingImage"""

	ImageModuleName = "Image"

	def __init__(self, filePath):
		super(ResizingImage, self).__init__()
		checkMoulePIL()
		self.filePath = filePath
		self.vLoc = self.hLoc = None
		self.vLen = self.hLen = 0
		self.resizingMode = DefaultImageResizingMode
		self.originalSize = (0, 0)

	####
	def parseResizingImage(self):
		#(name, scale, idiom, ext, sliceImage, subtype)
		imageAttributes = ImageModel.parseImageFileName(self.filePath)
		if not imageAttributes[4]:
			return None

		Image = __import__(ImageModuleName)
		image = Image.open(self.filePath)
		self.originalSize = image.size
		w, h = self.originalSize

		if not self._verifyImageformat(image):
			return None

		leftSlice = image.crop((0, 1, 1, h - 1))
		topSlice = image.crop((1, 0, w - 1, 1))

		leftResizing = self._resizingRange(leftSlice)
		topResizing = self._resizingRange(topSlice)

		(self.vLoc, self.vLen) = leftResizing[1]
		(self.hLoc, self.hLen) = topResizing[0]

		if self.vLoc is None and self.hLoc is None:
			return None

		return self

	# IMPORTANT!!! DONOT FORGET check if image is a canonical 9-patch image first!
	# Only 9-patch image can use this function. Otherwise the image will lose information
	def clipBorderAndOverwrite(self):
		Image = __import__(ImageModuleName)
		image = Image.open(self.filePath)
		w, h = image.size
		body = image.crop((1, 1, w - 1, h - 1))
		try:
			body.save(self.filePath)
			return True
		except Exception, e:
			print 'Exception: %s' % e
			return False

	def toDict(self):
		resizing = None
		w, h = (max(self.originalSize[0] - 2, 0), max(self.originalSize[1] - 2, 0))
		if self.vLoc is not None and self.hLoc is not None:
			resizing = {'mode': '9-part'}
			resizing['center'] = {'mode': self.resizingMode, 'width': self.hLen, 'height': self.vLen}
			resizing['capInsets'] = {'top': self.vLoc, 'left': self.hLoc, 'bottom': h - self.vLoc - self.vLen, 'right': w - self.hLoc - self.hLen}
		elif self.vLoc is not None:
			resizing = {'mode': '3-part-vertical'}
			resizing['center'] = {'mode': self.resizingMode, 'height': self.vLen}
			resizing['capInsets'] = {'top': self.vLoc, 'bottom': h - self.vLoc - self.vLen}
		elif self.hLoc is not None:
			resizing = {'mode': '3-part-horizontal'}
			resizing['center'] = {'mode': self.resizingMode, 'width': self.hLen}
			resizing['capInsets'] = {'left': self.hLoc, 'right': w - self.hLoc - self.hLen}
		else:
			Logger().warn('"%s" seems is not a resizable image!!! REMEMBER to confirm it!!!' % self.filePath)
		return resizing

	#########
	# 采用 anrdroid 的9.png 图片格式，
	# 图片最外边有一圈1像素宽的边框，必须是全透明的黑色(r:0, g:0, b:0, a:0)或者是完全不透明的白色(r:0xff, g:0xff, b:0xff, a:0xff)为底色
	# 图片拉伸区域的标注：
	#	横向拉伸区域： 在图片上边框用不透明的全黑色(r:0, g:0, b:0, a:0xff)标注拉伸区域
	#	纵向拉伸区域： 在图片左边框用不透明的全黑色(r:0, g:0, b:0, a:0xff)标注拉伸区域
	#	有边框和下边框保留， 全透明全黑色或者完全不透明全白色
	# NOTE：iOS 下的 @2x, @3x 图像， 边框仍然是1像素， 无需乘以 scale
	def _verifyImageformat(self, image):
		Image = __import__(ImageModuleName)

		if not image.mode == 'RGBA':
			image = image.convert('RGBA')
		if not image.mode == 'RGBA':
			Logger().error('Invalid image format, image format must to be RGBA. "%s"', self.filePath)
			return False

		isCanonicalFormat = True
		acceptedPixelValue = list(NinePatchImageBorderBGColors)
		acceptedPixelValue.append(NinePatchImageBorderMarkerColor)

		w, h = image.size
		pixels = []
		#border
		for i in xrange(1, w - 1):
			pixels.extend([(i, 0), (i, h - 1)])
		for i in xrange(1, h - 1):
			pixels.extend([(0, i), (w - 1, i)])
		for p in pixels:
			pv = image.getpixel(p)
			if pv not in acceptedPixelValue:
				print 'border color not valid: point:%s => %s' % (p, pv)
				isCanonicalFormat = False
				break
		if isCanonicalFormat:
			pixels = ((0, 0), (0, h - 1), (w - 1, 0), (w - 1, h - 1))
			for p in pixels:
				pv = image.getpixel(p)
				if pv not in NinePatchImageBorderBGColors:
					print 'horns color not valid: point:%s => %s' % (p, pv)
					isCanonicalFormat = False
					break
		return isCanonicalFormat

	def _resizingRange(self, cropImage):
		Image = __import__(ImageModuleName)
		img = cropImage

		if not img.mode == 'RGBA':
			img = img.convert('RGBA')
		if not img.mode == 'RGBA':
			Logger().error('Invalid image format, image format must to be RGBA. "%s"', self.filePath)
			return False

		#from itertools import chain
		(w, h) = img.size
		#print '_resizingRange: %s ' % self.filePath
		hLoc = vLoc = None
		hLen = vLen = 0
		if w == 1:
			for y in xrange(0, h):
				#r, g, b, a = img.getpixel((0, y))
				#print 'v: %s => (%s, %s, %s, %s)' % (y, r, g, b, a)
				if img.getpixel((0, y)) == NinePatchImageBorderMarkerColor:
					if vLoc is None:
						vLoc = y
					if not vLoc is None:
						vLen = vLen + 1
				elif not vLoc is None:
					break

		if h == 1:
			for x in xrange(0, w):
				#r, g, b, a = img.getpixel((x, 0))
				#print 'h: %s => (%s, %s, %s, %s)' % (x, r, g, b, a)
				if img.getpixel((x, 0)) == NinePatchImageBorderMarkerColor:
					if hLoc is None:
						hLoc = x
					if not hLoc is None:
						hLen = hLen + 1
				elif not hLoc is None:
					break
		return ((hLoc, hLen), (vLoc, vLen))


if __name__ == '__main__':
	Logger().info('Hello, welcome!')
	if len(sys.argv) > 1:
		if sys.argv[1] == 'make':
			XCAssets('/Users/baidu/workspace/test/xcassets-test').makeImagesets('/Users/baidu/workspace/github/BeeFramework/projects/example/example/view_iPhone/resource/img')
		elif sys.argv[1] == 'build':
			#XCAssets('/Users/baidu/workspace/test/xcassets-test').buildImagesets()
			XCAssets('/Users/baidu/workspace/testing/netdisk/netdisk/netdisk_iphone/netdisk_iPhone/Resources/Image_Resource.xcassets').buildImagesets(fastMode=False)

			#XCAssets('/Users/baidu/Desktop/Images.xcassets').buildImagesets(fastMode=False)
