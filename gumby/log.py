# log.py ---
#
# Filename: log.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Thu Oct 24 16:08:19 2013 (+0200)

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

from os import environ, path, chdir, makedirs
from sys import stdout, stderr
import logging
import logging.config
import sys


# TODO(emilon): Document this on the user manual
def setupLogging():
    # Allow to override the root handler log level from an environment variable.
    # @CONF_OPTION LOG_LEVEL: Override log level (for python that would be the root handler's log level only)
    log_level_override = environ.get("GUMBY_LOG_LEVEL", None)
    log_level = logging.INFO
    if log_level_override:
        print("Using custom logging level: %s" % log_level_override)
        log_level = getattr(logging, log_level_override)

    config_file = path.join(environ['EXPERIMENT_DIR'], "logger.conf")
    root = logging.getLogger()

    # Wipe out any existing handlers
    for handler in root.handlers:
        print("WARNING! handler present before when calling setupLogging, removing handler: %s" % handler.name)
        root.removeHandler(handler)

    if path.exists(config_file):
        print("Found a logger.conf, using it.")
        stdout.flush()
        logging.config.fileConfig(config_file)
    else:
        print("No logger.conf found.")
        stdout.flush()

        root.setLevel(log_level)

        stderr_handler = logging.StreamHandler(stderr)
        stderr_handler.setLevel(log_level)
        stderr_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(message)s"))
        root.addHandler(stderr_handler)


# log.py ends here
