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

from utils.logger import Logger
from utils.constants import MergeMode
from utils.constants import IdiomType
from utils.utils import __line__

# constant vars
DefaultImageResizingMode = 'fill'
DefaultContentsJsonVersion = 1
DefaultContentsJsonAuthor = 'xcode'

NinePatchImageBorderBGColors = ((0, 0, 0, 0), (255, 255, 255, 255), (255, 255, 255, 0))
NinePatchImageBorderMarkerColor = (0, 0, 0, 255)

SupportIdioms = (IdiomType.IPHONE, IdiomType.IPAD, IdiomType.UNIVERSAL)
SupportedScale = ('1x', '2x', '3x')


class ImageModel(object):
	def __init__(self, filePath, attributes=None):
		super(ImageModel, self).__init__()
		self.name = self.scale = self.idiom = self.ext = self.sliceImage = self.subtype = None
		self.filePath = filePath
		if filePath:
			attributes = ImageModel.parseImageFileName(filePath)
		if attributes and len(attributes) == 6:
			self.name, self.scale, self.idiom, self.ext, self.sliceImage, self.subtype = attributes
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
		if self.subtype == '-480h':
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
		if name:
			name = urllib.unquote(name)
			name = re.sub('[^\w\d_]', '_', name)
			while name.find('__') > 0:
				name = name.replace('__', '_')
		return (name, scale, idiom, ext, sliceImage, subtype)

	@staticmethod
	def imageModeFromDict(dic):
		model = ImageModel(None)
		(model.idiom, fn, model.scale, model.subtype, model.resizing) = utils.valueOrNoneFromDictWithKeys(dic, ('idiom', 'filename', 'scale', 'subtype', 'resizing'))
		(model.name, s, i, model.ext, model.sliceImage, t) = ImageModel.parseImageFileName(fn)
		return model

	@staticmethod
	def fileNameWithAttributes(attributes):
		(name, scale, idiom, ext, sliceImage, subtype) = attributes
		destName = ''
		if name:
			destName = name
		if sliceImage:
			destName = destName + '.9'
		if subtype:
			destName = destName + subtype
		if scale and not scale == '1x':
			destName = '%s@%s' % (destName, scale)
		if idiom and not idiom == IdiomType.UNIVERSAL:
			destName = '%s~%s' % (destName, idiom)
		if ext:
			destName = destName + ext
		else:
			destName = destName + '.png'
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

	def buildImagesets(self, fastMode=True):
		warnings = {}

		#inner function
		def _buildImageset(path):
			Logger().verbose('building imageset: "%s" ...' % path)
			originalJson = None
			jsonFile = os.path.join(path, 'Contents.json')
			if os.path.isfile(jsonFile):
				with open(jsonFile, 'rb') as fp:
					jsonString = fp.read()
					originalJson = json.loads(jsonString)

			imageFiles = [f for f in os.listdir(path) if self._isImageFile(os.path.join(path, f))]
			imageDic = {}
			_addSupportedDeviceIdiom(imageDic, IdiomType.UNIVERSAL)
			hasError = False
			for f in imageFiles:
				imgModel = ImageModel(os.path.join(path, f))
				if imgModel.sliceImage:
					resizingImage = ResizingImage(imgModel.filePath).parseResizingImage()
					if not resizingImage and not originalJson:
						Logger().error('Image "%s" has 9-patch image name subfix, but It seems not a canonical 9-patch format. Please check it manually.' % imgModel.filePath)
						sys.exit(1)
					elif not resizingImage:
						#这是一个已经处理过的9.png 图片, 保留原来 json 中的 resizing 信息
						originalInfo = _findImageInfoFromOriginalJson(imgModel, originalJson)
						if not originalInfo or not 'resizing' in originalInfo:
							Logger().error('Lost information for image:"%s". '
								'This image should be a resizable image, '
								'but we could not find any information from the original Contents.json,'
								'please check it manually.' % imgModel.filePath)
							sys.exit(1)
						imgModel.resizing = originalInfo['resizing']
					else:
						imgModel.resizing = resizingImage.toDict()
						imgModel.needRewriteSliceImage = True
				## add imageModel to imageDic
				if not _addImageModelToImagesset(imageDic, imgModel):
					hasError = True
			if not hasError:
				_buildJsonFile(imageDic, path)
				for k, imgModel in imageDic.items():
					if imgModel.needRewriteSliceImage:
						if not ResizingImage(imgModel.filePath).clipBorderAndOverwrite():
							Logger().warn('Failed to rewrite resizing image: "%s".' % imgModel.filePath)
						else:
							with open(jsonFile, 'a') as fp:
								fp.write('')  # make sure Content.json is the last modified file

		def _findImageInfoFromOriginalJson(imageModel, originalJson):
			if not type(originalJson) is dict or not 'images' in originalJson:
				print 'original json not a dict'
				return None
			for imgJson in originalJson['images']:
				attrs = utils.valueOrNoneFromDictWithKeys(imgJson, ('filename', 'scale', 'idiom', 'subtype'))
				if attrs == (imageModel.canonicalFileName(), imageModel.scale, imageModel.idiom, imageModel.subtype):
					return imgJson
			return None

		def _keyForImage(imageModel):
			return '%s.%s.%s' % (imageModel.idiom, imageModel.scale, imageModel.subtype)

		def _addImageModelToImagesset(imagesDic, imageModel):
			hasError = False
			key = _keyForImage(imageModel)
			if not key in imagesDic:
				_addSupportedDeviceIdiom(imagesDic, imageModel.idiom)
				imagesDic[key] = imageModel
			elif imagesDic[key].name is None:
				imagesDic[key] = imageModel
			else:
				self._appendArrayItemToDicForKey(warnings, os.path.dirname(imageModel.filePath), [imagesDic[key].canonicalFileName(), imageModel.canonicalFileName()])
				hasError = True
			return not hasError

		##
		def _buildJsonFile(imageDic, path):
			images = [img.toDict() for key, img in imageDic.items()]
			contents = {'images': images, 'info': {'version': DefaultContentsJsonVersion, 'author':  DefaultContentsJsonAuthor}}
			jsonFile = os.path.join(path, 'Contents.json')
			fp = open(jsonFile, 'wb')
			if fp:
				jstr = json.dumps(contents, sort_keys=True, indent=2)
				if jstr:
					fp.write(jstr)
					fp.close()
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
				abspath = os.path.join(path, f)
				imagesetName, pathExt = os.path.splitext(abspath)
				if os.path.isdir(abspath) and pathExt == '.imageset':
					needUpdate = False
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
		fileCmd = utils.pathForShell('file')
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
	def __init__(self, filePath):
		super(ResizingImage, self).__init__()
		self._checkMoulePIL()
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

		import Image
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
		import Image
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
		import Image

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
		import Image
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

	def _checkMoulePIL(self):
		## Check dependence of PIL, we need this module to process images
		ImageModuleName = "Image"
		try:
			__import__(ImageModuleName)
		except Exception:
			Logger().warn('Module "%s" is not installed, try to install it automatically ...' % ImageModuleName)
			easy_install = utils.pathForCmd('easy_install')
			if easy_install is None:
				Logger().error('Automatic installation can not be completed, please install %s manually.' % ImageModuleName)
				sys.exit(1)

			p = subprocess.Popen(['sudo', easy_install, 'PIL'], stdout=subprocess.PIPE)
			stdout, stderr = p.communicate()
			if p.returncode != 0:
				if stderr:
					Logger().verbose(stderr)
				Logger().error('Automatic installation can not be completed, please install %s manually.' % ImageModuleName)
				Logger().info('If installation failed caused by "\'X11/Xlib.h\' file not found", Please try to run "xcode-select --install" to install Xcode command-line tools first and then try again.')
				sys.exit(1)

			Logger().info('========= Install %s completed ========' % ImageModuleName)
		## END of checking dependence for PIL


if __name__ == '__main__':
	Logger().info('Hello, welcome!')
	#XCAssets('').makeImagesets('')
	#print 'match name:%s' % ImageModel.fileNameWithAttributes(('*', '2x', 'ipad', '.*', None, None))
	#dic = ResizingImage('/Users/baidu/workspace/github/MCLogTest/popup_bg_1.9.png').slicingInfo()
	#var_dump(dic)

	if len(sys.argv) > 1:
		if sys.argv[1] == 'make':
			XCAssets('/Users/baidu/workspace/test/xcassets-test').makeImagesets('/Users/baidu/workspace/test/images')
		elif sys.argv[1] == 'build':
			XCAssets('/Users/baidu/workspace/test/xcassets-test').buildImagesets()
