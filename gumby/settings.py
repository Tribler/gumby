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

from configobj import ConfigObj
from validate import Validator

conf_spec = '''
workspace_dir = string
head_nodes = list(default=[])
tracker_cmd = string(default="run_tracker.sh")
config_server_cmd = string(default="")
tracker_run_remote = boolean(default=True)
tracker_port = integer(min=1025, max=65535, default=7788)

local_setup_cmd = string(default="gorilla_setup.sh")
remote_setup_cmd = string(default="das4_setup.sh")

local_instance_cmd = string(default="")
remote_instance_cmd = string(default="")

use_local_venv = boolean(default=True)
use_local_systemtap = boolean(default=False)
virtualenv_dir = string(default="$HOME/venv")

spectraperf_db_path = string(default="")
'''


def loadConfig(path):
    spec = conf_spec.splitlines()
    config = ConfigObj(path, configspec=spec)
    validator = Validator()
    config.validate(validator)
    # TODO: Find a better way to do this (If the default value for a list is an empty list, it just doesn't set the value at all)
    if 'head_nodes' not in config:
        config["head_nodes"] = []
    return config

#
# settings.py ends here
