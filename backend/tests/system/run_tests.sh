#!/bin/bash

echo "Running tests with option: $1"

# Define test groups
VETERAN_TESTS="tests/system/test_veteran_player_projections.py"
ROOKIE_TESTS="tests/system/test_rookie_projections.py"
TEAM_ADJUST_TESTS="tests/system/test_team_adjustments.py"
SCENARIO_TESTS="tests/system/test_scenarios.py"
OVERRIDE_TESTS="tests/system/test_overrides.py"
ALL_COMPONENT_TESTS="$VETERAN_TESTS $ROOKIE_TESTS $TEAM_ADJUST_TESTS $SCENARIO_TESTS $OVERRIDE_TESTS"
PIPELINE_TESTS="tests/system/test_complete_season_pipeline.py"

# Run based on parameter
case "$1" in
  "veteran")
    echo "Running veteran projection tests"
    python -m pytest $VETERAN_TESTS -v
    ;;
  "rookie")
    echo "Running rookie projection tests"
    python -m pytest $ROOKIE_TESTS -v
    ;;
  "team")
    echo "Running team adjustment tests"
    python -m pytest $TEAM_ADJUST_TESTS -v
    ;;
  "scenario")
    echo "Running scenario tests"
    python -m pytest $SCENARIO_TESTS -v
    ;;
  "override")
    echo "Running override tests"
    python -m pytest $OVERRIDE_TESTS -v
    ;;
  "components")
    echo "Running all component tests"
    python -m pytest $ALL_COMPONENT_TESTS -v
    ;;
  "pipeline")
    echo "Running pipeline tests"
    python -m pytest $PIPELINE_TESTS -v
    ;;
  *)
    echo "Usage: ./run_tests.sh [veteran|rookie|team|scenario|override|components|pipeline]"
    echo "Invalid option: $1"
    exit 1
    ;;
esac