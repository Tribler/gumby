#!/usr/bin/env python
# run_in_env.py ---
#
# Filename: run_in_env.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Fri Aug 23 17:37:32 2013 (+0200)

# Commentary:
#
#
#
#

# Change Log:
#
#
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

# Code:

from os import path, chdir, environ, makedirs
from glob import glob
from subprocess import call
import sys
import shlex


def extend_var(env, var, value, prepend=True):
    if var in env:
        if prepend:
            env[var] = value + ':' + env[var]
        else:
            env[var] = env[var] + value if env[var].endswith(':') else env[var] + ':' + value
    else:
        env[var] = value


def expand_var(var):
    return path.expanduser(path.expandvars(var))

# move to the project root dir, which is the parent of the one where this file is located (PROJECT_DIR/scripts/THIS_FILE)
project_dir = path.abspath(path.join(path.dirname(path.abspath(__file__)), '..', '..'))
print 'Project root is:', project_dir

scripts_dir = path.join(project_dir, "gumby/scripts")
r_scripts_dir = path.join(scripts_dir, "r")

sys.path.append(path.join(project_dir, "gumby"))
from gumby.settings import configToEnv, loadConfig

chdir(project_dir)

if len(sys.argv) >= 3:
    conf_path = path.abspath(sys.argv[1])
    if not path.exists(conf_path):
        print "Error: The specified configuration file (%s) doesn't exist." % conf_path
        exit(2)
    config = loadConfig(conf_path)
    experiment_dir = path.abspath(path.dirname(path.abspath(conf_path)))
else:
    print "Usage:\n%s EXPERIMENT_CONFIG COMMAND" % sys.argv[0]
    exit(1)

# TODO: Update environ instead of copying it, we are using some stuff
# from this script anyways.
env = environ.copy()
env.update(configToEnv(config))

env['PROJECT_DIR'] = project_dir
environ['PROJECT_DIR'] = project_dir

env['EXPERIMENT_DIR'] = experiment_dir
environ['EXPERIMENT_DIR'] = experiment_dir

# Add project dir to PYTHONPATH
extend_var(env, "PYTHONPATH", project_dir)

# Add gumby dir to PYTHONPATH
extend_var(env, "PYTHONPATH", path.join(project_dir, "gumby"))

# Add gumby scripts dir to PATH
extend_var(env, "PATH", scripts_dir)
extend_var(environ, "PATH", scripts_dir)

# Add the experiment dir to PATH so we can call custom scripts from there
extend_var(env, "PATH", experiment_dir)

# Add ~/R to the R search path
extend_var(env, "R_LIBS_USER", expand_var("$HOME/R"))
# Export the R scripts path
extend_var(env, "R_SCRIPTS_PATH", r_scripts_dir)
extend_var(environ, "R_SCRIPTS_PATH", r_scripts_dir)

# @CONF_OPTION VIRTUALENV_DIR: Virtual env to activate for the experiment (default is ~/venv)
# Enter virtualenv in case there's one
if "VIRTUALENV_DIR" in env and path.exists(expand_var(env["VIRTUALENV_DIR"])):
    venv_dir = path.abspath(expand_var(env["VIRTUALENV_DIR"]))
    print "Enabling virtualenv at", venv_dir
    extend_var(env, "LD_LIBRARY_PATH", path.join(venv_dir, "inst/lib"))
    extend_var(env, "LD_LIBRARY_PATH", path.join(venv_dir, "lib"))  # TODO: Check if this one is needed
    extend_var(env, "PATH", path.join(venv_dir, "inst/bin"))

    # This is a replacement for running venv/bin/activate
    env["VIRTUAL_ENV"] = venv_dir
    extend_var(env, "PATH", path.join(venv_dir, "bin"))

    # export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$EXTRA_LD_LIBRARY_PATH # TODO: Seems that this is no longer necessary

    # TODO: Only do this if we _can_ run systemtap on this machine.
    print "Generating stap files:"
    # Path substitution for the tapsets, needs to be done even in case of USE_LOCAL_SYSTEMTAP
    # is disabled as we could be using systemtap from within the experiment.
    tapset_dir = path.join(venv_dir, "tapsets")
    if not path.exists(tapset_dir):
        makedirs(tapset_dir)
    for source_file in glob("gumby/scripts/stp/tapsets/*"):
        dest_file = path.join(tapset_dir, path.basename(path.splitext(source_file)[0]))
        print "  %s  ->  %s" % (source_file, dest_file)
        open(dest_file, "w").write(open(source_file, 'r').read().replace("__VIRTUALENV_PATH__", venv_dir))

# @CONF_OPTION OUTPUT_DIR: Dir where to write all the output generated from the experiment (default is experiment_dir/output)
# Create the experiment output dir if necessary
if 'OUTPUT_DIR' in env:
    # Convert the output dir to an absolute path to make it easier for
    # the rest of scripts to write into it.
    output_dir = path.abspath(env['OUTPUT_DIR'])
    env['OUTPUT_DIR'] = output_dir
    environ['OUTPUT_DIR'] = output_dir
    if not path.exists(output_dir):
        makedirs(output_dir)

# Run the actual command
cmd = expand_var(" ".join(sys.argv[2:]))
print "Running", cmd

exit(call((shlex.split(cmd)), env=env))

#
# run_in_env.py ends here
