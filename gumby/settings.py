# settings.py ---
#
# Filename: settings.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Tue Jul  9 18:05:03 2013 (+0200)

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

from getpass import getuser
from hashlib import md5
from os import path, environ, curdir
from validate import Validator

from configobj import ConfigObj

conf_spec = '''
experiment_name = string
workspace_dir = string(default="./")
remote_workspace_dir = string(default="./")
output_dir = string(default="output")
head_nodes = list(default=[])

tracker_cmd = string(default="")
tracker_run_remote = boolean(default=False)
tracker_port = integer(min=1025, max=65535, default=7788)

experiment_server_run_remote = boolean(default=False)
experiment_server_cmd = string(default="")

local_setup_cmd = string(default="")
remote_setup_cmd = string(default="das4_setup.sh")

local_instance_cmd = string(default="")
remote_instance_cmd = string(default="")

post_process_cmd = string(default="")

use_local_venv = boolean(default=True)
use_remote_venv = boolean(default=True)
virtualenv_dir = string(default="$HOME/venv3")
'''


def loadConfig(file_path):
    spec = conf_spec.splitlines()
    config = ConfigObj(file_path, configspec=spec)
    validator = Validator()
    config.validate(validator)
    # TODO: Find a better way to do this (If the default value for a list is an empty list, it just doesn't set the value at all)
    if 'head_nodes' not in config:
        config["head_nodes"] = []
    for key, value in config.iteritems():
        # If any config option has the special value __unique_port__, compute a unique port for it by hashing the user
        # ID, the experiment name, the experiment execution dir and the config option name.
        if value == '__unique_port__':
            md5sum = md5()
            md5sum.update(getuser().encode('utf-8'))
            md5sum.update(config['experiment_name'].encode('utf-8'))
            md5sum.update(path.abspath(curdir).encode('utf-8'))
            md5sum.update(key.encode('utf-8'))
            config[key] = int(md5sum.hexdigest()[-16:], 16) % 20000 + 20000

    # Override config options with env. variables.
    revalidate = False
    for key, value in environ.items():
        if key.startswith("GUMBY_"):
            name = key[6:].lower()  # "GUMBY_".len()
            config[name] = value
            revalidate = True
    if revalidate:
        config.validate(validator)
    return config


def configToEnv(config):
    """
    Processes a dictionary of config options so it can be exported as env. variables when running a subprocess.
    """
    env = {}
    for name, val in config.iteritems():
        env[name.upper()] = path.expanduser(path.expandvars(str(val)))
    return env
#
# settings.py ends here
