#!/usr/bin/python
#encoding:utf-8
#Filename: pbxprojParser.py

import os
import sys
import subprocess
import json

from logger import Logger


class XCProject(object):
	def __init__(self, project_path):
		super(XCProject, self).__init__()
		project_path = os.path.normpath(os.path.abspath(project_path))
		isValid = os.path.isdir(project_path) and os.path.splitext(project_path)[1] == '.xcodeproj'
		if not isValid:
			Logger().error('"%s" is not a valid xcode project' % project_path)
			sys.exit(1)

		self.projectHome = os.path.dirname(project_path)
		p = subprocess.Popen(['/usr/bin/plutil', '-convert', 'json', '-o', '-', os.path.join(project_path, 'project.pbxproj')], stdout=subprocess.PIPE)
		stdout, stderr = p.communicate()
		if p.returncode != 0:
			Logger().error('Can not parse project file')
			Logger().info(stdout)
			sys.exit(1)

		self.json = json.loads(stdout)
		self.rootObjectID = str(self.childrenWithKeyPathAtNode(('rootObject',)))
		mainGroupPath = self.childrenWithKeyPathAtNode(('objects', self.rootObjectID, 'projectDirPath'))
		if mainGroupPath is None:
			mainGroupPath = ''
		self.completeObjectsPath(str(self.childrenWithKeyPathAtNode(('objects', self.rootObjectID, 'mainGroup'))), mainGroupPath)

	def getfiles(self, args={'sourceTree': '<group>'}):
		args['isa'] = 'PBXFileReference'
		return self.getObjects(args)

	def getObjects(self, args={}):
		objects = [o for o in self.json['objects'].values()]

		def checkObject(o):
			for k in args.keys():
				matches = k in o and o[k] == args[k]
				if not matches:
					return False
			return True
		return filter(checkObject, objects)

	def productName(self, target):
		targets = self.childrenWithKeyPathAtNode(('objects', self.rootObjectID, 'targets'))
		for target in targets:
			if self.childrenWithKeyPathAtNode(('objects', self.rootObjectID, 'attributes', 'TargetAttributes', str(target))):
				return str(self.childrenWithKeyPathAtNode(('objects', str(target), 'productName')))
		return None

	def organizationName(self):
		name = self.childrenWithKeyPathAtNode(('objects', self.rootObjectID, 'attributes', 'ORGANIZATIONNAME'))
		return name if name else ''

	def projectClassPrefix(self):
		projPrefix = self.childrenWithKeyPathAtNode(('objects', self.rootObjectID, 'attributes', 'CLASSPREFIX'))
		if not projPrefix:
			projPrefix = 'MYAPP'
		return projPrefix.upper()

	def completeObjectsPath(self, parentID, parentPath, groups=''):
		parent = self.childrenWithKeyPathAtNode(('objects', parentID))
		if not parent:
			Logger().error('key:"objects" in object:%s' % parentID)
			sys.exit(1)
		if 'path' in parent:
			if 'sourceTree' in parent and parent['sourceTree'] == '<group>':
				parentPath = os.path.normpath(os.path.join(parentPath, parent['path']))
			elif 'sourceTree' in parent and parent['sourceTree'] == 'SOURCE_ROOT':
				parentPath = parent['path']
		parent['full_path'] = parentPath

		if 'isa' in parent and parent['isa'] == 'PBXGroup':
			if 'path' in parent:
				groups = os.path.normpath(os.path.join(groups, parent['path']))
			elif 'name' in parent:
				groups = os.path.normpath(os.path.join(groups, parent['name']))

		parent['groups'] = groups
		if 'children' in parent:
			for childID in parent['children']:
				self.completeObjectsPath(str(childID), parentPath, groups)

	def childrenWithKeyPathAtNode(self, path=(), o=None):
		if o is None:
			o = self.json

		for p in path:
			if p in o:
				o = o[p]
			else:
				return None
		return o
