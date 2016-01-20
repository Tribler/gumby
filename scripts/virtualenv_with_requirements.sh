#!/usr/bin/env bash
# Filename: virtualenv_with_requirements.sh
# Description:
# Author: Wouter Smit
# Maintainer:
# Created: Tue Jan 19 2015

# Commentary:
# %*% Creates a virtual environment with all dependencies listed in
# %*% a requirements.txt file found in the experiment folder.
# %*% Uses the VIRTUALENV_DIR variable in the config options.
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
#
#

# Code :

# @CONF_OPTION REQUIREMENTS_FILE: Set the requirements file in the experiment directory to read the dependencies from. (default is 'requirements.txt')

if [ -z "$REQUIREMENTS_FILE" ]; then
    REQUIREMENTS_FILE=$EXPERIMENT_DIR/requirements.txt;
fi

DONE_VAR=".done"

# Fail fast if the requirements do not exist.
if ! [  -a $REQUIREMENTS_FILE ]; then
    echo "Could not find requirements in experiment directory";
    exit 1
fi

# Try to reuse the environment if it already exists
if [ -d $VIRTUALENV_DIR ] && [ -a $VIRTUALENV_DIR/$DONE_VAR ]; then
    # Compute md5 hash of requirements to compare the already existing 
    # environments installation
    NEW_HASH=$(md5sum $REQUIREMENTS_FILE)
    OLD_HASH=$(cat $VIRTUALENV_DIR/$DONE_VAR)
    echo "testing hashes"
    if [ "$OLD_HASH"=="$NEW_HASH" ]; then
        echo "Reusing previously created virtual environment"
	exit 0
    fi
fi
    virtualenv --system-site-packages --clear $VIRTUALENV_DIR
    $VIRTUALENV_DIR/bin/easy_install --upgrade pip
    
    source $VIRTUALENV_DIR/bin/activate
    pip install -r $EXPERIMENT_DIR/$REQUIREMENTS_FILE
    
    deactivate
    
    virtualenv --relocatable $VIRTUALENV_DIR
    
    # Write the new hash to the DONE file for future checks
    echo $NEW_HASH > $VIRTUALENV_DIR/$DONE_VAR
    
#
# virtualenv_with_requirements.sh ends here
