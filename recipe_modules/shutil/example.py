# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'shutil',
]

def RunSteps(api):
  api.shutil.rmtree('foo')


def GenTests(api):
  yield api.test('basic')
