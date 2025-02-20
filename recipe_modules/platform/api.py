# Copyright 2013 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

"""Mockable system platform identity functions."""

import sys
import platform
import multiprocessing

from recipe_engine import recipe_api


def norm_bits(arch):
  return 64 if '64' in str(arch) else 32


def get_arch():
  arch = platform.machine()
  return 'arm' if ('arm' in arch or 'aarch' in arch) else 'intel'


class PlatformApi(recipe_api.RecipeApi):
  """
  Provides host-platform-detection properties.

  Mocks:
    * name (str): A value equivalent to something that might be returned by
      sys.platform.
    * bits (int): Either 32 or 64.
  """

  def __init__(self, **kwargs):
    super(PlatformApi, self).__init__(**kwargs)
    self._name = PlatformApi.normalize_platform_name(sys.platform)

    self._arch = get_arch()
    self._bits = norm_bits(platform.machine())

    if self._test_data.enabled:
      # Default to linux/64, unless test case says otherwise.
      self._name = PlatformApi.normalize_platform_name(
        self._test_data.get('name', 'linux'))
      self._bits = norm_bits(self._test_data.get('bits', 64))
      self._cpu_count = self._test_data.get('cpu_count', 2)
      self._arch = self._test_data.get('arch', 'intel')
    else:  # pragma: no cover
      # platform.machine is based on running kernel. It's possible to use 64-bit
      # kernel with 32-bit userland, e.g. to give linker slightly more memory.
      # Distinguish between different userland bitness by querying
      # the python binary.
      if (self._name == 'linux' and
          self._bits == 64 and
          platform.architecture()[0] == '32bit'):
        self._bits = 32
      # On Mac, the inverse of the above is true: the kernel is 32-bit but the
      # CPU and userspace both are capable of running 64-bit programs.
      elif (self._name == 'mac' and
            self._bits == 32 and
            platform.architecture()[0] == '64bit'):
        self._bits = 64

      self._cpu_count = multiprocessing.cpu_count()

  @property
  def is_win(self):
    """Returns True iff the recipe is running on Windows."""
    return self.name == 'win'

  @property
  def is_mac(self):
    """Returns True iff the recipe is running on OS X."""
    return self.name == 'mac'

  @property
  def is_linux(self):
    """Returns True iff the recipe is running on Linux."""
    return self.name == 'linux'

  @property
  def name(self):
    """Returns the current platform name which will be in:
      * win
      * mac
      * linux
    """
    return self._name

  @property
  def bits(self):
    """Returns the bitness of the userland for the current system (either 32 or
    64 bit).

    TODO: If anyone needs to query for the kernel bitness, another accessor
    should be added.
    """
    return self._bits

  @property
  def arch(self):
    """Returns the current CPU architecture.

    TODO: This is currently always hard-coded to 'intel'... Apparently no one
    has actually needed this function?
    """
    return self._arch

  @property
  def cpu_count(self):
    """The number of CPU cores, according to multiprocessing.cpu_count()."""
    return self._cpu_count

  @staticmethod
  def normalize_platform_name(plat):
    """One of python's sys.platform values -> 'win', 'linux' or 'mac'."""
    if plat.startswith('linux'):
      return 'linux'
    elif plat.startswith(('win', 'cygwin')):
      return 'win'
    elif plat.startswith(('darwin', 'mac')):
      return 'mac'
    else:  # pragma: no cover
      raise ValueError('Don\'t understand platform "%s"' % plat)
