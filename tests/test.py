import os
import sys
ModuleRoot = os.path.abspath(os.path.join(__file__, '../..'))
if os.path.isdir(ModuleRoot) and not ModuleRoot in sys.path:
    sys.path.append(ModuleRoot)

from xcodeproj.pbxproj import pbxproj

class TestObj(object):
    def __init__(self, name):
        self.isa = name
        print(u'{0}:{1}'.format(self.__class__, self.name))


class SubObj(TestObj):
    def __init__(self, name):
        super(SubObj, self).__init__(name)


if __name__ == '__main__':
    proj = pbxproj.XcodeProj.load('/Users/alexlee/Desktop/test_pbxproj.xcodeproj')
    proj.validate()
    proj.save(tofile=u'/Users/alexlee/Desktop/test_pbxproj-1.xcodeproj/project.pbxproj')
