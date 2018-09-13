#!/bin/bash

# The PWD is the root of the project, so create the path to the jmeter test file
jmeter_file_path="$PWD/gumby/experiments/tribler/api_benchmark/$TEST_RUNNER_FILE"

# jmeter has no output directory option, so CD into this directory and run it in there.
pushd $OUTPUT_DIR

# Run jmeter headless (-n option) and specify the file using -t
jmeter -n -t $jmeter_file_path

popd
