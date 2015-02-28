#!/usr/bin/python
#encoding:utf-8

from template_function import enum
from template_function import singleton

LogAdapter = enum(SHELL=0, XCODE=1)


@singleton
class Logger(object):
	"""a better way to show outputs"""
	global LogAdapter
	adapter = LogAdapter.SHELL

	def __init__(self):
		self.adapter = LogAdapter.SHELL

	def verbose(self, message):
		if self.adapter == LogAdapter.SHELL:
			print '\033[2m-[VERBOSE] %s\033[0m' % message

	def info(self, message):
		if self.adapter == LogAdapter.XCODE:
			print message
		else:
			print '\033[32m-[INFO] %s\033[0m' % message

	def warn(self, message):
		if self.adapter == LogAdapter.XCODE:
			print 'warning: %s' % message
		else:
			print '\033[33m-[WARN] %s\033[0m' % message

	def error(self, message):
		if self.adapter == LogAdapter.XCODE:
			print 'error: %s' % message
		else:
			import sys
			sys.stderr.write('\033[1;31m-[ERROR] %s\033[0m\r\n' % message)
