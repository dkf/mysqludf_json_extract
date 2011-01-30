#!/usr/bin/env python

import sys
import unittest
from ctypes import *

l = CDLL(sys.argv[1])
l.json_extract.restype = c_char_p

STRING_RESULT = c_uint(0)

class UDF_INIT(Structure):
  _fields_ = [
    ("maybe_null", c_char),
    ("decimals", c_uint),
    ("max_length", c_ulong),
    ("ptr", c_void_p),
    ("const_item", c_char),
    ("extension", c_void_p)]

class UDF_ARGS(Structure):
  _fields_ = [
    ("arg_count", c_uint),
    ("arg_type", POINTER(c_uint)),
    ("args", POINTER(c_char_p)),
    ("lengths", POINTER(c_ulong)),
    ("maybe_null", POINTER(c_char)),
    ("attributes", POINTER(c_char_p)),
    ("attribute_lengths", POINTER(c_uint)),
    ("extension", c_void_p)]

TwoArgsType = c_uint * 2
TwoArgs = c_char_p * 2
TwoLengths = c_ulong * 2

c_string = create_string_buffer

class TestBasic(unittest.TestCase):
  def assertResult(self, expected, spec, s):
    """expected is None to indicate a null result, False to indicate an error"""
    initid = UDF_INIT(c_char('\x01'), c_uint(32), c_ulong(100), None, c_char('\x00'), None)
    args = UDF_ARGS(
      c_uint(2),
      TwoArgsType(STRING_RESULT, STRING_RESULT),
      TwoArgs(c_char_p(spec), c_char_p(s)),
      TwoLengths(c_ulong(len(spec)), c_ulong(len(s))),
      pointer(c_char('\x01')), None, None, None)

    self.assertEquals(0, l.json_extract_init(pointer(initid), pointer(args), None))

    length = pointer(c_uint(0))
    result = c_char_p('\x00' * 255)
    is_null = pointer(c_char('\x00'))
    error = pointer(c_char('\x00'))

    actual = l.json_extract(
          pointer(initid), pointer(args),
          result, length, is_null, error)

    if error.contents.value == '\x00':
      if is_null.contents.value == '\x01':
        self.assertEquals(expected, None)
      elif is_null.contents.value == '\x00':
        self.assertEquals(expected, actual)
      else:
        self.fail("is_null is %s, not 0 or 1" % is_null.contents.value)
    elif error.contents.value == '\x01':
      self.assertEquals(expected, False)
    else:
      self.fail("error is %s, not 0 or 1" % error.contents.value)

    l.json_extract_deinit(pointer(initid))

  def test_single_str(self):
    self.assertResult("foo", "a", "{\"a\":\"foo\"}")
    self.assertResult("foo", "abcdef", "{\"abcdef\":\"foo\"}")
  def test_single_null(self):
    self.assertResult("null", "a", "{\"a\":null}")
    self.assertResult("null", "abcdef", "{\"abcdef\":null}")
  def test_single_bool(self):
    self.assertResult("false", "a", "{\"a\":false}")
    self.assertResult("true", "abcdef", "{\"abcdef\":true}")
  def test_single_num(self):
    self.assertResult("42", "a", "{\"a\":42}")
    self.assertResult("42.356", "abcdef", "{\"abcdef\":42.356}")
  def test_bigger(self):
    self.assertResult("42", "z.bc.def", '{"a":31,"d":[null],"z":{"bc":{"def":42}}}')
  def test_array_stack_bug(self):
    self.assertResult("42", "z.bc.def", '{"a":31,"d":[null,2,{"a":1}],"z":{"bc":{"def":42}}}')
  def test_result_str_too_big(self):
    self.assertResult("a" * 255, "a", '{"a":"%s"}' % ("a" * 300))
  def test_result_num_too_big(self):
    self.assertResult("1" + ("0" * 254), "a", '{"a":"%s"}' % ("1" + ("0" * 300)))
  def test_array_start(self):
    self.assertResult(None, "a", '[{"a":1}]')
  def test_obj_result(self):
    self.assertResult(None, "a", '{"a":[1]}')
  def test_map_result(self):
    self.assertResult(None, "a", '{"a":{"b":1}}')
  def test_double_periods(self):
    self.assertResult("bar", "ab....cdef.g...", '{"zc":{},"ab":{"cdef":{"g":"bar"}}}')
  def test_unparsable(self):
    self.assertResult(None, "a", '{"a"::::1}')
    self.assertResult(None, "a", '{_"a":1}')
    self.assertResult(None, "a", '{{}"a":1}')

if __name__ == "__main__":
  unittest.main(argv=[sys.argv[0]] + sys.argv[2:])
