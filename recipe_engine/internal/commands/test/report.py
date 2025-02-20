# -*- coding: utf-8 -*-
# Copyright 2019 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

"""Internal helpers for reporting test status to stdout."""


import collections
import datetime
import logging
import sys

from cStringIO import StringIO

import attr
import coverage

from backports.shutil_get_terminal_size import get_terminal_size


@attr.s
class Reporter(object):
  _use_emoji = attr.ib()
  _is_train = attr.ib()

  _symbol_count = attr.ib(default=0)
  _long_err_buf = attr.ib(factory=StringIO)

  _start_time = attr.ib(factory=datetime.datetime.now)

  _symbol_count = attr.ib(default=0)

  # all emoji are 2 columns wide
  _symbol_width = attr.ib()
  @_symbol_width.default
  def _symbol_width_default(self):
    return 2 if self._use_emoji else 1

  # default to 80 cols if we can't figure out the width (or are on a bot), and
  # then prevent _symbol_max from ever falling below 1 (to avoid division by 0).
  _symbol_max = attr.ib()
  @_symbol_max.default
  def _symbol_max_default(self):
    return max(1, (get_terminal_size().columns or 80) / self._symbol_width)

  _verbose = attr.ib()
  @_verbose.default
  def _verbose_default(self):
    return logging.getLogger().level < logging.WARNING

  def short_report(self, outcome_msg):
    """Prints all test results from `outcome_msg` to stdout.

    Detailed error messages (if any) will be accumulated in this reporter.

    NOTE: Will report and then raise SystemExit if the outcome_msg contains an
    'internal_error', as this indicates that the test harness is in an invalid
    state.

    Args:

      * outcome_msg (Outcome proto) - The message to report.

    Raises SystemExit if outcome_msg has an internal_error.
    """
    # Global error; this means something in the actual test execution code went
    # wrong.
    if outcome_msg.internal_error:
      # This is pretty bad.
      print 'ABORT ABORT ABORT'
      print 'Global failure(s):'
      for failure in outcome_msg.internal_error:
        print '  ', failure
      sys.exit(1)

    for test_name, test_result in outcome_msg.test_results.iteritems():
      _print_summary_info(
          self._verbose, self._use_emoji, test_name, test_result)
      _print_detail_info(self._long_err_buf, test_name, test_result)

    self._symbol_count += 1
    if not self._verbose:
      if (self._symbol_count % self._symbol_max) == 0:
        self._symbol_count = 0
        print

  def final_report(self, cov, outcome_msg):
    """Prints all final information about the test run to stdout. Raises
    SystemExit if the tests have failed.

    Args:

      * cov (coverage.Coverage|None) - The accumulated coverage data to report.
        If None, then no coverage analysis/report will be done. Coverage less than
        100% counts as a test failure.
      * outcome_msg (Outcome proto) - Consulted for uncovered_modules and
        unused_expectation_files. coverage_percent is also populated as a side
        effect. Any uncovered_modules/unused_expectation_files count as test
        failure.

    Side-effects: Populates outcome_msg.coverage_percent.

    Raises SystemExit if the tests failed.
    """
    fail = self._long_err_buf.tell() > 0

    print
    sys.stdout.write(self._long_err_buf.getvalue())

    # For some integration tests we have repos which don't actually have any
    # recipe files at all. We skip coverage measurement if cov has no data.
    if cov and cov.get_data().measured_files():
      covf = StringIO()
      try:
        outcome_msg.coverage_percent = cov.report(
            file=covf, show_missing=True, skip_covered=True)
      except coverage.CoverageException as ex:
        print '%s: %s' % (ex.__class__.__name__, ex)
      if int(outcome_msg.coverage_percent) != 100:
        fail = True
        print covf.getvalue()
        print 'FATAL: Insufficient coverage (%.2f%%)' % (
          outcome_msg.coverage_percent,)
        print

    duration = (datetime.datetime.now() - self._start_time).total_seconds()
    print '-' * 70
    print 'Ran %d tests in %0.3fs' % (len(outcome_msg.test_results), duration)
    print

    if outcome_msg.uncovered_modules:
      fail = True
      print '------'
      print 'ERROR: The following modules lack any form of test coverage:'
      for modname in outcome_msg.uncovered_modules:
        print '  ', modname
      print
      print 'Please add test recipes for them (e.g. recipes in the module\'s'
      print '"tests" subdirectory).'
      print

    if outcome_msg.unused_expectation_files:
      fail = True
      print '------'
      print 'ERROR: The following expectation files have no associated test case:'
      for expect_file in outcome_msg.unused_expectation_files:
        print '  ', expect_file
      print

    if fail:
      print '------'
      print 'FAILED'
      print
      if not self._is_train:
        print 'NOTE: You may need to re-train the expectation files by running:'
        print
        print '  ./recipes.py test train'
        print
        print 'This will update all the .json files to have content which matches'
        print 'the current recipe logic. Review them for correctness and include'
        print 'them with your CL.'
      sys.exit(1)

    print 'OK'


# Internal helper stuff


FIELD_TO_DISPLAY = collections.OrderedDict([
  # pylint: disable=bad-whitespace
  ('internal_error', (False, 'internal testrunner error',           '🆘', '!')),

  ('bad_test',       (False, 'test specification was bad/invalid',  '🛑', 'S')),
  ('crash_mismatch', (False, 'recipe crashed in an unexpected way', '🔥', 'E')),
  ('check',          (False, 'failed post_process check(s)',        '❌', 'X')),
  ('diff',           (False, 'expectation file has diff',           '⚡', 'D')),

  ('removed',        (True,  'removed expectation file',            '🌟', 'R')),
  ('written',        (True,  'updated expectation file',            '💾', 'D')),

  (None,             (True,  '',                                    '✅', '.'))
])


def _check_field(test_result, field_name):
  if field_name is None:
    return FIELD_TO_DISPLAY[field_name], None

  for descriptor, value in test_result.ListFields():
    if descriptor.name == field_name:
      return FIELD_TO_DISPLAY[field_name], value

  return (None, None, None, None), None


def _print_summary_info(verbose, use_emoji, test_name, test_result):
  # Pick the first populated field in the TestResults.Results
  for field_name in FIELD_TO_DISPLAY:
    (success, verbose_msg, emj, txt), _ = _check_field(test_result, field_name)
    icon = emj if use_emoji else txt
    if icon:
      break

  if verbose:
    msg = '' if not verbose_msg else ' (%s)' % verbose_msg
    print '%s ... %s%s' % (test_name, 'ok' if success else 'FAIL', msg)
  else:
    sys.stdout.write(icon)
  sys.stdout.flush()


def _print_detail_info(err_buf, test_name, test_result):
  verbose_msg = None

  def _header():
    print >>err_buf, '=' * 70
    print >>err_buf, 'FAIL (%s) - %s' % (verbose_msg, test_name)
    print >>err_buf, '-' * 70

  for field in ('internal_error', 'bad_test', 'crash_mismatch'):
    (_, verbose_msg, _, _), lines = _check_field(test_result, field)
    if lines:
      _header()
      for line in lines:
        print >>err_buf, line
      print >>err_buf

  (_, verbose_msg, _, _), lines_groups = _check_field(test_result, 'check')
  if lines_groups:
    _header()
    for group in lines_groups:
      for line in group.lines:
        print >>err_buf, line
      print >>err_buf

  (_, verbose_msg, _, _), lines = _check_field(test_result, 'diff')
  if lines:
    _header()
    for line in lines.lines:
      print >>err_buf, line
    print >>err_buf
