#!/usr/bin/python
#encoding:utf-8
#Filename: constants.py

from template_function import enum

MergeMode = enum(MERGE=0, IGNORE=1, OVERWRITE=2)
IdiomType = enum(UNIVERSAL='universal', IPHONE='iphone', IPAD='ipad')