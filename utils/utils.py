#!/usr/bin/python
#encoding:utf-8
#Filename: utils.py

import subprocess
import os
import sys
import inspect
from logger import Logger


def trimComment(filePath):
	trimCommentShell = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), 'trim_comments.sh')))
	if not os.path.isfile(trimCommentShell):
		Logger().error('File "%s" not exists!' % trimCommentShell)
		sys.exit(1)
	p = subprocess.Popen([trimCommentShell, filePath], stdout=subprocess.PIPE)
	stdout, stderr = p.communicate()
	if p.returncode != 0:
		Logger().error('Fail to trim comments, file: "%s"' % filePath)
		Logger().info(stderr)
	return stdout
#end of func:trimComment


def valueOrNoneFromDictWithKeys(dic, keys):
	values = []
	for k in keys:
		if k in dic:
			values.append(dic[k])
		else:
			values.append(None)
	return tuple(values)


def pathForShell(cmd):
	p = subprocess.Popen(['whereis', cmd], stdout=subprocess.PIPE)
	stdout, stderr = p.communicate()
	if p.returncode == 0:
		return stdout.split('\n')[0]
	return None
#end of func:pathForShell


def __line__():
	caller = inspect.stack()[1]
	return int(caller[2])


def __function__():
	caller = inspect.stack()[1]
	return caller[3]





