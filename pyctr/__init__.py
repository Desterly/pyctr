# This file is a part of pyctr.
#
# Copyright (c) 2017-2021 Ian Burgwin
# This file is licensed under The MIT License (MIT).
# You can find the full license text in LICENSE in the root of this project.

from collections import namedtuple

__author__ = 'ihaveamac'
__copyright__ = 'Copyright (c) 2017-2021 Ian Burgwin'
__license__ = 'MIT'

VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')
version_info = VersionInfo(major=0, minor=5, micro=1, releaselevel='final', serial=0)
__version__ = '0.5.1'
