import os
import sys
ModuleRoot = os.path.abspath(os.path.join(__file__, '../..'))
if os.path.isdir(ModuleRoot) and not ModuleRoot in sys.path:
    sys.path.append(ModuleRoot)

from xcodeproj.pbxproj import pbxproj


if __name__ == '__main__':
    proj = pbxproj.XcodeProj.create(u'/Users/alexlee/Desktop/test-2', u'test-2', u'8.0')
    proj.validate()
    proj.save()

