# Copyright 2015 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

from recipe_engine import recipe_test_api

class PlatformTestApi(recipe_test_api.RecipeTestApi):
  @recipe_test_api.mod_test_data
  @staticmethod
  def name(name):
    assert name in ('win', 'linux', 'mac'), 'unknown platform %r' % (name,)
    return name

  @recipe_test_api.mod_test_data
  @staticmethod
  def bits(bits):
    assert bits in (32, 64), 'unknown bitness %r' % (bits,)
    return bits

  @recipe_test_api.mod_test_data
  @staticmethod
  def arch(arch):
    assert arch in ('intel', 'arm'), 'unknown arch %r' % (arch,)
    return arch

  @recipe_test_api.mod_test_data
  @staticmethod
  def cpu_count(cpu_count):
    assert isinstance(cpu_count, int), 'bad type %r' % (type(cpu_count),)
    assert cpu_count > 0, 'bad cpu_count %r' % (cpu_count,)
    return cpu_count

  def __call__(self, name, bits, arch='intel'):
    return self.name(name) + self.bits(bits) + self.arch(arch)

