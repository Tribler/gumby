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

from twisted.python.log import msg, FileLogObserver, textFromEventDict, _safeFormat, removeObserver, addObserver, startLogging
from twisted.python import util

class ColoredFileLogObserver(FileLogObserver):
    CANCEL_COLOR = "\x1b[0m"
    RED_NORMAL = "\x1b[31m"
    RED_BOLD = "\x1b[31;1m"
    GREEN_NORMAL = "\x1b[32m"
    GREEN_BOLD = "\x1b[32;1m"
    GREY_NORMAL = "\x1b[37m"

    def __init__(self, f=None):
        if f is None:
            FileLogObserver.__init__(self, sys.stdout)
        else:
            FileLogObserver.__init__(self, f)

        self.timeFormat = "%H:%M:%S"

    def _colorize(self, text, color=GREY_NORMAL):
        return color + text + ColoredFileLogObserver.CANCEL_COLOR

    def emit(self, eventDict):
        text = textFromEventDict(eventDict)
        if text is None:
            return

        timeStr = self._colorize(
            self.formatTime(eventDict['time']),
            ColoredFileLogObserver.GREY_NORMAL)
        fmtDict = {
            'system': eventDict['system'],
            'text': text.replace("\n", "\n\t")}
        systemStr = self._colorize(
            _safeFormat("[%(system)s]", fmtDict),
            ColoredFileLogObserver.GREY_NORMAL)
        textStr = _safeFormat("%(text)s", fmtDict)

        if textStr.startswith("SSH"):
            t = textStr.find("STDERR:")
            if t != -1:
                textStr = self._colorize(
                    textStr[t + 8:],
                    ColoredFileLogObserver.RED_BOLD)
            else:
                textStr = self._colorize(
                    textStr[textStr.find("STDOUT:") + 8:],
                    ColoredFileLogObserver.GREEN_BOLD)
            # only text for incoming data
            msgStr = textStr + "\n"
        else:
            # add system to the local logs
            # TODO: Make system more useful, not just "SSHChannel...".
            msgStr = systemStr + " " + textStr + "\n"

        util.untilConcludes(self.write, timeStr + " " + msgStr)
        util.untilConcludes(self.flush)  # Hoorj!


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


# TODO(emilon): Document this on the user manual
def setupLogging():
    # Allow to override the root handler log level from an environment variable.
    # @CONF_OPTION LOG_LEVEL: Override log level (for python that would be the root handler's log level only)
    log_level_override = environ.get("GUMBY_LOG_LEVEL", None)
    log_level = logging.INFO
    if log_level_override:
        print "Using custom logging level: %s" % log_level_override
        log_level = getattr(logging, log_level_override)

    config_file = path.join(environ['EXPERIMENT_DIR'], "logger.conf")
    root = logging.getLogger()

    # Wipe out any existing handlers
    for handler in root.handlers:
        print "WARNING! handler present before when calling setupLogging, removing handler: %s" % handler.name
        root.removeHandler(handler)

    if path.exists(config_file):
        print "Found a logger.conf, using it."
        stdout.flush()
        logging.config.fileConfig(config_file)
    else:
        print "No logger.conf found."
        stdout.flush()

        root.setLevel(log_level)

        stderr_handler = logging.StreamHandler(stderr)
        stderr_handler.setLevel(log_level)
        stderr_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(message)s"))
        root.addHandler(stderr_handler)

    observer = PythonLoggingObserver('root', defaultLogLevel=logging.INFO)
    observer.start()


# log.py ends here
