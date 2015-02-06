#!/usr/bin/python
#encoding:utf-8
#Filename: test.py

import os
import sys

root=os.path.abspath(os.path.dirname(__file__))
root=os.path.dirname(root)

if not root in sys.path:
	sys.path.append(root)

import utils



utils.Logger().warn('this is a warnning message')
utils.Logger().adapter = utils.LogAdapter.SHELL
utils.Logger().error('Error message')
utils.trimComment(__file__)