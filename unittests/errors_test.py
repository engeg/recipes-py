#!/usr/bin/env vpython
# Copyright 2014 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

import json
import os
import subprocess

import test_env


class ErrorsTest(test_env.RecipeEngineUnitTest):
  def _test_cmd(self, deps, cmd, asserts=None, retcode=0):
    if cmd[0] == 'run':
      path = self.tempfile()
      cmd = [cmd[0]] + ['--output-result-json', path] + cmd[1:]

    try:
      output, returncode = deps.main_repo.recipes_py(*cmd)

      if asserts:
        asserts(output)
      self.assertEqual(
          returncode, retcode,
          '%d != %d.\noutput:\n%s' % (returncode, retcode, output))

      if cmd[0] == 'run':
        if not os.path.exists(path):
          return

        with open(path) as tf:
          raw = tf.read()
          data = None
          if raw:
            data = json.loads(raw)
        return data
    finally:
      if cmd[0] == 'run':
        if os.path.exists(path):
          os.unlink(path)

  def test_missing_dependency(self):
    deps = self.FakeRecipeDeps()
    with deps.main_repo.write_recipe('foo') as recipe:
      recipe.DEPS = ['aint_no_thang']

    def _assert_nomodule(output):
      self.assertRegexpMatches(
        output, r"No module named 'aint_no_thang' in repo 'main'.")

    self._test_cmd(
        deps, ['run', 'foo'], retcode=1, asserts=_assert_nomodule)

  def test_missing_module_dependency(self):
    deps = self.FakeRecipeDeps()
    with deps.main_repo.write_recipe('foo') as recipe:
      recipe.DEPS = ['le_module']

    with deps.main_repo.write_module('le_module') as mod:
      mod.DEPS.append('love')

    def _assert_nomodule(output):
      self.assertRegexpMatches(output, r"No module named 'love' in repo 'main'")

    self._test_cmd(
        deps, ['run', 'foo'], retcode=1, asserts=_assert_nomodule)

  def test_no_such_recipe(self):
    deps = self.FakeRecipeDeps()
    result = self._test_cmd(
        deps, ['run', 'nooope'], retcode=1)
    self.assertIsNotNone(result['failure']['exception'])

  def test_syntax_error(self):
    deps = self.FakeRecipeDeps()
    with deps.main_repo.write_file('recipes/foo.py') as buf:
      buf.write('''
      DEPS = [ (sic)
      ''')

    def assert_syntaxerror(output):
      self.assertRegexpMatches(output, r'SyntaxError')

    self._test_cmd(deps, ['test', 'run', '--filter', 'foo'],
        asserts=assert_syntaxerror, retcode=1)
    self._test_cmd(deps, ['test', 'train', '--filter', 'foo'],
        asserts=assert_syntaxerror, retcode=1)
    self._test_cmd(deps, ['run', 'foo'],
        asserts=assert_syntaxerror, retcode=1)

  def test_missing_path(self):
    deps = self.FakeRecipeDeps()
    with deps.main_repo.write_recipe('missing_path') as recipe:
      recipe.DEPS.append('recipe_engine/path')
      recipe.RunSteps.write('''
        api.step('do it, joe', ['echo', 'JOE'],
                 cwd=api.path['bippityboppityboo'])
      ''')
      recipe.GenTests.write('''
        yield api.test('basic')
      ''')

    def _assert_keyerror(output):
      self.assertRegexpMatches(
          output, r"KeyError: 'Unknown path: bippityboppityboo'")

    self._test_cmd(deps, ['test', 'train', '--filter', 'missing_path'],
                   asserts=_assert_keyerror, retcode=1)
    self._test_cmd(deps, ['test', 'run', '--filter', 'missing_path'],
                   asserts=_assert_keyerror, retcode=1)
    self._test_cmd(deps, ['run', 'missing_path'],
                   asserts=_assert_keyerror, retcode=1)

  def test_engine_failure(self):
    deps = self.FakeRecipeDeps()
    with deps.main_repo.write_file('recipes/print_step_error.py') as buf:
      buf.write('''
      DEPS = ['recipe_engine/step']

      from recipe_engine import step_runner

      def bad_print_step(self, step_stream, step, env):
        raise Exception("Buh buh buh buh bad to the bone")

      def GenTests(api):
        pass

      def RunSteps(api):
        step_runner.SubprocessStepRunner._print_step = bad_print_step
        try:
          api.step('Be good', ['echo', 'Sunshine, lollipops, and rainbows'])
        finally:
          api.step.active_result.presentation.status = 'WARNING'
      ''')

    self._test_cmd(deps, ['run', 'print_step_error'],
      asserts=lambda output: self.assertRegexpMatches(
          output,
          r'(?s)Recipe engine bug.*Buh buh buh buh bad to the bone'),
      retcode=2)

  def test_missing_method(self):
    deps = self.FakeRecipeDeps()
    with deps.main_repo.write_file('recipes/no_gen_tests.py') as buf:
      buf.write('''
      def RunSteps(api):
        pass
      ''')
    self._test_cmd(deps, ['run', 'no_gen_tests'],
      asserts=lambda output: self.assertRegexpMatches(
          output,
          r'(?s)misspelled GenTests'),
      retcode=1)

    with deps.main_repo.write_file('recipes/no_run_steps.py') as buf:
      buf.write('''
      def GenTests(api):
        pass
      ''')
    self._test_cmd(deps, ['run', 'no_run_steps'],
      asserts=lambda output: self.assertRegexpMatches(
          output,
          r'(?s)misspelled RunSteps'),
      retcode=1)


  def test_unconsumed_assertion(self):
    # There was a regression where unconsumed exceptions would not be detected
    # if the exception was AssertionError.
    deps = self.FakeRecipeDeps()
    with deps.main_repo.write_recipe('unconsumed_assertion') as recipe:
      recipe.DEPS = []
      recipe.GenTests.write('''
        yield api.test('basic') + api.expect_exception('AssertionError')
      ''')

    self._test_cmd(deps, [
        'test', 'train', '--filter', 'unconsumed_assertion'],
      asserts=lambda output: self.assertRegexpMatches(output, 'Unconsumed'),
      retcode=1)

  def test_run_recipe_help(self):
    deps = self.FakeRecipeDeps()
    with deps.main_repo.write_recipe('do_nothing') as recipe:
      recipe.DEPS = []

    def _assert_output(output):
      self.assertRegexpMatches(
          output, r'from the root of a \'main\' checkout')
      self.assertRegexpMatches(
          output, r'\./recipes\.py run .* do_nothing')
    self._test_cmd(deps, ['run', 'do_nothing'],
      asserts=_assert_output)


if __name__ == '__main__':
  test_env.main()
