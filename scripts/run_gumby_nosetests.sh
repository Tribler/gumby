#!/bin/bash

parentdir=$(dirname $0)
cd $parentdir/../..
PYTHONPATH=gumby:tribler:$PYTHONPATH nosetests2 --with-coverage --cover-html --cover-erase --cover-branches --cover-package=gumby --cover-package=experiments gumby/gumby/tests
