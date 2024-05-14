# This file is a part of pyctr.
#
# Copyright (c) 2017-2023 Ian Burgwin
# This file is licensed under The MIT License (MIT).
# You can find the full license text in LICENSE in the root of this project.

import os
from math import ceil
from sys import platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List

__all__ = ['windows', 'macos', 'readle', 'readbe', 'roundup', 'config_dirs']

windows = platform == 'win32'
macos = platform == 'darwin'


def readle(b: bytes) -> int:
    """Convert little-endian bytes to an int."""
    return int.from_bytes(b, 'little')


def readbe(b: bytes) -> int:
    """Convert big-endian bytes to an int."""
    return int.from_bytes(b, 'big')


def roundup(offset: int, alignment: int) -> int:
    """Round up a number to a provided alignment."""
    return int(ceil(offset / alignment) * alignment)

def decompose(flag, value):
    """Extract all members from the value."""
    # _decompose is only called if the value is not named
    not_covered = value
    negative = value < 0
    members = []
    for member in flag:
        member_value = member.value
        if member_value and member_value & value == member_value:
            members.append(member)
            not_covered &= ~member_value
    if not negative:
        tmp = not_covered
        while tmp:
            flag_value = 2 ** _high_bit(tmp)
            if flag_value in flag._value2member_map_:
                members.append(flag._value2member_map_[flag_value])
                not_covered &= ~flag_value
            tmp &= ~flag_value
    if not members and value in flag._value2member_map_:
        members.append(flag._value2member_map_[value])
    members.sort(key=lambda m: m._value_, reverse=True)
    if len(members) > 1 and members[0].value == value:
        # we have the breakdown, don't need the value member itself
        members.pop(0)
    return members, not_covered

_home = os.path.expanduser('~')
config_dirs: 'List[str]' = [os.path.join(_home, '.3ds'), os.path.join(_home, '3ds')]
if windows:
    config_dirs.insert(0, os.path.join(os.environ.get('APPDATA'), '3ds'))
elif macos:
    config_dirs.insert(0, os.path.join(_home, 'Library', 'Application Support', '3ds'))
