#!/usr/bin/env python

import sys
import unittest
from ctypes import *
from json import dumps
from random import randint, choice
from types import *

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

class TestBase(unittest.TestCase):
  def udf_init(self):
    return UDF_INIT(c_char('\x01'), c_uint(32), c_ulong(100), None, c_char('\x00'), None)
  def udf_args(self, spec, json):
    return UDF_ARGS(
      c_uint(2),
      TwoArgsType(STRING_RESULT, STRING_RESULT),
      TwoArgs(c_char_p(spec), c_char_p(json)),
      TwoLengths(c_ulong(len(spec)), c_ulong(len(json))),
      pointer(c_char('\x01')), None, None, None)
  def do_init(self, initid_p, args_p):
    return l.json_extract_init(initid_p, args_p, None)
  def assertResult(self, expected, spec, json):
    """expected is None to indicate a null result, False to indicate an error"""
    initid = self.udf_init()
    args = self.udf_args(spec, json)

    self.assertEquals(0, self.do_init(pointer(initid), pointer(args)))

    length = pointer(c_uint(0))
    result = c_char_p('\x00' * max(255, len(json)))
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
        self.assertEquals(len(actual), length.contents.value)
      else:
        self.fail("is_null is %s, not 0 or 1" % is_null.contents.value)
    elif error.contents.value == '\x01':
      self.assertEquals(expected, False)
    else:
      self.fail("error is %s, not 0 or 1" % error.contents.value)

    l.json_extract_deinit(pointer(initid))

class TestBasic(TestBase):
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
  def test_array_start(self):
    self.assertResult(None, "a", '[{"a":1}]')
  def test_obj_result(self):
    self.assertResult("[1]", "a", '{"a":[1]}')
    self.assertResult("[1]", "a", '{"a":[1]}')
  def test_map_result(self):
    self.assertResult('{"b":1}', "a", '{"a":{"b":1}}')
  def test_double_periods(self):
    self.assertResult("bar", "ab....cdef.g...", '{"zc":{},"ab":{"cdef":{"g":"bar"}}}')
  def test_unparsable(self):
    self.assertResult(None, "a", '{"a"::::1}')
    self.assertResult(None, "a", '{_"a":1}')
    self.assertResult(None, "a", '{{}"a":1}')
  def test_substr(self):
    self.assertResult(None, "a", '{"abc":1}')
    self.assertResult(None, "abc", '{"a":1}')

class TestFuzz(TestBase):
  def select_path(self, o, acc):
    if type(o) is DictType:
      i = randint(0, 3)
      if i > 1 or not acc:
        k = choice(o.keys())
        acc.append(k)
        return self.select_path(o[k], acc)
      else:
        return o
    else:
      return o
  def serialize_val(self, o):
    if type(o) is DictType or type(o) is ListType:
      return dumps(o, separators=(',',':'))
    elif type(o) is BooleanType:
      if o is True:
        return "true"
      else:
        return "false"
    elif type(o) is NoneType:
      return "null"
    elif type(o) is StringType:
      return o
    else:
      return str(o)
  def gen_val(self):
    o = {}
    r = randint(0, 12)
    self.count += 1
    k = "k%s" % self.count
    # obj, array, null, bool, num, string
    if r < 2: # obj
      o[k] = self.gen_val()
    elif r < 4: # array
      a = []
      for i in range(0, randint(1, 5)):
        a.append(self.gen_val())
      o[k] = a
    elif r < 6: # null
      o[k] = None
    elif r < 8: # bool
      if randint(0, 1) == 0:
        o[k] = False
      else:
        o[k] = True
    elif r < 10: # num
      o[k] = randint(0, 1000)
    else: # string
      o[k] = k
    return o

  def test_fuzz(self):
    for i in range(1, 1000):
      o = {}
      self.count = 0
      for j in range(1, 50):
        self.count += 1
        k = "k%s" % self.count
        o[k] = self.gen_val()
      o["v1"] = {"y2":-1}
      self.assertResult("-1", "v1.y2", dumps(o, sort_keys=True))
  def test_arr_fuzz(self):
    for i in range(1, 1000):
      o = {}
      self.count = 0
      for j in range(1, 50):
        self.count += 1
        k = "k%s" % self.count
        o[k] = self.gen_val()
      o["v1"] = [self.gen_val(), self.gen_val()]
      self.assertResult(
        dumps(o["v1"], separators=(',',':')),
        "v1", dumps(o, sort_keys=True))
  def test_obj_fuzz(self):
    for i in range(1, 1000):
      o = {}
      self.count = 0
      for j in range(1, 50):
        self.count += 1
        k = "k%s" % self.count
        o[k] = self.gen_val()
      o["v1"] = {"y1":self.gen_val(), "y2":self.gen_val()}
      o["v2"] = {"y1":self.gen_val(), "y2":self.gen_val()}
      self.assertResult(
        dumps(o["v1"]["y1"], separators=(',',':')),
        "v1.y1", dumps(o, sort_keys=True))
      path = []
      v = self.select_path(o, path)
      self.assertResult(
        self.serialize_val(v),
        ".".join(path),
        dumps(o))

if __name__ == "__main__":
  unittest.main(argv=[sys.argv[0]] + sys.argv[2:])
