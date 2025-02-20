# Copyright 2019 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.


def execute_test_case(recipe_deps, recipe_name, test_data):
  """Executes a single test case.

  Args:

    * recipe_deps (RecipeDeps)
    * recipe_name (basestring) - The recipe to run.
    * test_data (TestData) - The test data to use for the simulated run.

  Returns a 4-tuple of:
    * The result of RecipeEngine.run_steps
    * SimulationStepRunner.export_steps_ran()
    * SimulationStreamEngine.annotations
    * Uncaught exception triggered by recipe code or None
  """
  # pylint: disable=too-many-locals

  # Late imports to avoid importing 'PB'.
  from ..engine import RecipeEngine
  from ..engine_env import FakeEnviron
  from ..step_runner.sim import SimulationStepRunner
  from ..stream.invariants import StreamEngineInvariants
  from ..stream.simulator import SimulationStreamEngine

  step_runner = SimulationStepRunner(test_data)
  simulator = SimulationStreamEngine()
  stream_engine = StreamEngineInvariants.wrap(simulator)

  props = test_data.properties.copy()
  props['recipe'] = str(recipe_name)
  # Disable source manifest uploading by default.
  if '$recipe_engine/source_manifest' not in props:
    props['$recipe_engine/source_manifest'] = {}
  if 'debug_dir' not in props['$recipe_engine/source_manifest']:
    props['$recipe_engine/source_manifest']['debug_dir'] = None

  environ = FakeEnviron()
  for key, value in test_data.environ.iteritems():
    environ[key] = value

  result, uncaught_exception = RecipeEngine.run_steps(
      recipe_deps, props, stream_engine, step_runner, environ, '',
      num_cores=8, test_data=test_data, skip_setup_build=True)

  return result, step_runner.export_steps_ran(), simulator.annotations, \
      uncaught_exception
