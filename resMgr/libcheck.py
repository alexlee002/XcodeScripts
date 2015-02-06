#!/usr/bin/python
#encoding:utf-8

import sys
import os
import json
import shutil
import glob
import subprocess
from var_dump import var_dump

myModulePath=os.path.join(os.path.dirname(__file__), "..")
if not myModulePath in sys.path:
	sys.path.append(myModulePath)
import utils
from utils.logger import Logger
from utils.pbxprojParser import XCProject


def checkProjectLibArch(xcproj, supportArch=()):
	for lib in xcproj.getfiles({'lastKnownFileType':'archive.ar'}):
	#for lib in xcproj.getObjects({'fileType':'archive.ar'}):
		utils.Logger().info('checking %s ...' % lib['path'])
		if not lib.has_key('full_path'):
			utils.Logger().error('can not find path for lib:')
			var_dump(lib)
			utils.Logger().info('')
		else:
			fullPath = None
			if os.path.exists(lib['full_path']):
				fullPath = lib['full_path']
			elif os.path.exists(os.path.join(xcproj.projectHome, lib['full_path'])):
				fullPath = os.path.join(xcproj.projectHome, lib['full_path'])
			if not fullPath:
				utils.Logger().error('lib path not found:')
				var_dump(lib)
				utils.Logger().info('')
			else:
				cmd = 'lipo -detailed_info %s | grep \'architecture\' | awk  \'{printf "%%s|", $NF}\'' % fullPath
				p = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
				stdout, stderr = p.communicate()
				if stdout:
					archs = stdout.split('|')
					for arch in supportArch:
						if not arch in archs:
							utils.Logger().error('[X] %s not support arch:%s; path:%s' % (lib['path'], arch, lib['full_path']))
				else:
					utils.Logger().error('check lib information:')
					var_dump(lib)
					utils.Logger().info('')
					if stderr:
						utils.Logger().verbose(stderr)




if __name__ == '__main__':
	xcproj = XCProject('/Users/baidu/workspace/Baidu/netDisk/netdisk/netdisk_iphone/netdisk_iPhone.xcodeproj')

	checkProjectLibArch(xcproj, ('armv7', 'arm64'))

