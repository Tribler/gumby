#!/bin/bash

# This scripts runs the pylint checker on a given input directory

# @CONF_OPTION PYLINT_IGNORE_DIRS: Specify which directories should be ignored by Pylint (default is '')

# @CONF_OPTION PYLINT_RUN_DIR: Specify from which directory pylint should run (default is $PWD)
if [ ! -z "$PYLINT_RUN_DIR" ]; then
cd $PYLINT_RUN_DIR
fi

echo "Running pylint (ignored directories: ${PYLINT_IGNORE_DIRS})"
pylint --ignore=${PYLINT_IGNORE_DIRS} --output-format=parseable --reports=y Tribler > ${OUTPUT_DIR}/pylint.out 2> ${OUTPUT_DIR}/pylint.log
