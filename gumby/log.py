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

from os import environ, path, chdir, makedirs, symlink
from sys import stdout
import logging.config
import logging

from twisted.python.log import textFromEventDict, removeObserver, addObserver, msg, startLogging


class PythonLoggingObserver(object):

    """
    Output twisted messages to Python standard library L{logging} module.

    WARNING: specific logging configurations (example: network) can lead to
    a blocking system. Nothing is done here to prevent that, so be sure to not
    use this: code within Twisted, such as twisted.web, assumes that logging
    does not block.
    """

    def __init__(self, loggerName="twisted", defaultLogLevel=logging.DEBUG):
        """
        @param loggerName: identifier used for getting logger.
        @type loggerName: C{str}
        """
        self.default_loglevel = defaultLogLevel
        self.logger = logging.getLogger(loggerName)

    def emit(self, eventDict):
        """
        Receive a twisted log entry, format it and bridge it to python.

        By default the logging level used is info; log.err produces error
        level, and you can customize the level by using the C{logLevel} key::

        >>> log.msg('debugging', logLevel=logging.DEBUG)

        """
        if 'logLevel' in eventDict:
            level = eventDict['logLevel']
        elif eventDict['isError']:
            level = logging.ERROR
        else:
            level = self.default_loglevel
        text = textFromEventDict(eventDict)
        if text is None:
            return
        self.logger.log(level, text)

    def start(self):
        """
        Start observing log events.
        """
        addObserver(self.emit)

    def stop(self):
        """
        Stop observing log events.
        """
        removeObserver(self.emit)


def setupLogging():
    observer = PythonLoggingObserver()
    observer.start()
    config_file = path.join(environ['EXPERIMENT_DIR'], "logger.conf")
    # TODO(emilon): Document this on the user manual
    if path.exists(config_file):
        msg("This experiment has a logger.conf, using it.")
        logging.config.fileConfig(config_file)
    else:
        msg("No logger.conf found for this experiment.")

#
# log.py ends here
