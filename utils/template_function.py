#!/usr/bin/python
#encoding:utf-8


# 用装饰器实现单例
def singleton(cls, *args, **kw):
	instances = {}

	def _singleton():
		if cls not in instances:
			instances[cls] = cls(*args, **kw)
		return instances[cls]
	return _singleton


def enum(**enums):
	return type('Enum', (), enums)
