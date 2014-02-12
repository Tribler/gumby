#!/bin/bash -xe
FOLDER=/home/jenkins/workspace
PY_FOLDER=/home/jenkins/venv/lib/python2.7/

sed -e "s~$FOLDER~~g" $1 > $1.tmp && mv $1.tmp $1


sed -e "s~$PY_FOLDER~%PYTHON%~g" $1 > $1.tmp && mv $1.tmp $1 


