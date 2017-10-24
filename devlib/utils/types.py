#    Copyright 2014-2015 ARM Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""
Routines for doing various type conversions. These usually embody some higher-level
semantics than are present in standard Python types (e.g. ``boolean`` will convert the
string ``"false"`` to ``False``, where as non-empty strings are usually considered to be
``True``).

A lot of these are intened to stpecify type conversions declaratively in place like
``Parameter``'s ``kind`` argument. These are basically "hacks" around the fact that Python
is not the best language to use for configuration.

"""
import math

from devlib.utils.misc import isiterable, to_identifier, ranges_to_list, list_to_mask


def identifier(text):
    """Converts text to a valid Python identifier by replacing all
    whitespace and punctuation."""
    return to_identifier(text)


def boolean(value):
    """
    Returns bool represented by the value. This is different from
    calling the builtin bool() in that it will interpret string representations.
    e.g. boolean('0') and boolean('false') will both yield False.

    """
    false_strings = ['', '0', 'n', 'no', 'off']
    if isinstance(value, basestring):
        value = value.lower()
        if value in false_strings or 'false'.startswith(value):
            return False
    return bool(value)


def integer(value):
    """Handles conversions for string respresentations of binary, octal and hex."""
    if isinstance(value, basestring):
        return int(value, 0)
    else:
        return int(value)


def numeric(value):
    """
    Returns the value as number (int if possible, or float otherwise), or
    raises ``ValueError`` if the specified ``value`` does not have a straight
    forward numeric conversion.

    """
    if isinstance(value, int):
        return value
    try:
        fvalue = float(value)
    except ValueError:
        raise ValueError('Not numeric: {}'.format(value))
    if not math.isnan(fvalue) and not math.isinf(fvalue):
        ivalue = int(fvalue)
        if ivalue == fvalue:  # yeah, yeah, I know. Whatever. This is best-effort.
            return ivalue
    return fvalue


class caseless_string(str):
    """
    Just like built-in Python string except case-insensitive on comparisons. However, the
    case is preserved otherwise.

    """

    def __eq__(self, other):
        if isinstance(other, basestring):
            other = other.lower()
        return self.lower() == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __cmp__(self, other):
        if isinstance(basestring, other):
            other = other.lower()
        return cmp(self.lower(), other)

    def format(self, *args, **kwargs):
        return caseless_string(super(caseless_string, self).format(*args, **kwargs))


def bitmask(value):
    if isinstance(value, basestring):
        value = ranges_to_list(value)
    if isiterable(value):
        value = list_to_mask(value)
    if not isinstance(value, int):
        raise ValueError(value)
    return value
