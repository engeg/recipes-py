# Copyright 2019 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.


def header(input_api):
  """Returns the expected license header regexp for this project."""
  current_year = int(input_api.time.strftime('%Y'))
  allowed_years = (str(s) for s in reversed(xrange(2011, current_year + 1)))
  years_re = '(' + '|'.join(allowed_years) + ')'
  license_header = (
    r'.*? Copyright %(year)s The LUCI Authors\. '
      r'All rights reserved\.\n'
    r'.*? Use of this source code is governed under the Apache License, '
      r'Version 2\.0\n'
    r'.*? that can be found in the LICENSE file\.(?: \*/)?\n'
  ) % {
    'year': years_re,
  }
  return license_header


def CommonChecks(input_api, output_api):
  results = []

  results.extend(input_api.canned_checks.PanProjectChecks(
      input_api, output_api, license_header=header(input_api),
      excluded_paths=[
          r'.+_pb2\.py',
      ],
  ))

  # explicitly run these independently because they update files on disk and are
  # called implicitly with the other tests. The vpython check is nominally
  # locked with a file lock, but updating the protos, etc. of recipes.py is not.
  recipes_py = input_api.os_path.join(
      input_api.PresubmitLocalPath(), 'recipes.py')
  run_first = (
    input_api.canned_checks.CheckVPythonSpec(input_api, output_api) + [
      input_api.Command(
          'Compile recipe protos',
          ['python', recipes_py, 'fetch'],
          {},
          output_api.PresubmitError,
      ),
    ])

  for cmd in run_first:
    result = input_api.thread_pool.CallCommand(cmd)
    if result:
      results.append(result)

  # Now run all the unit tests in parallel.
  results.extend(input_api.RunTests(
      input_api.canned_checks.GetUnitTestsInDirectory(
          input_api, output_api, 'unittests', whitelist=[r'.+_test\.py'])
  ))

  return results


CheckChangeOnUpload = CommonChecks
CheckChangeOnCommit = CommonChecks
