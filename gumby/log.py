import inspect
import logging
from os.path import normcase

from twisted.python.log import PythonLoggingObserver, textFromEventDict

# TODO(vladum): Maybe we can locate these source files w/o importing modules.
import twisted.python.log
import twisted.python.threadable
_srcfiles = [
    inspect.getsourcefile(twisted.python.threadable),
    inspect.getsourcefile(twisted.python.log),
    inspect.getsourcefile(inspect.currentframe()),
    logging._srcfile
]

class GumbyLogger(logging.Logger):
    """
    Logger that walks up a few more levels on the call stack.

    The original Python Logger doesn't work very nice with Twisted - it always
    reports "log" as the module of all messages. We need to walk a few more
    levels (see _srcfiles) to get the right originating module.
    """
    def findCaller(self):
        f = logging.currentframe().f_back
        rv = "(unknown file)", 0, "(unknown function)"
        while hasattr(f, "f_code"):
            co = f.f_code
            filename = normcase(co.co_filename)
            if filename in _srcfiles:
                f = f.f_back
                continue
            rv = (filename, f.f_lineno, co.co_name)
            break
        return rv

class ColoredFormatter(logging.Formatter):
    """
    Nice and shiny Python logging colored formatter.
    """
    _START_NORMAL = "\033[0;%dm"
    _START_BOLD = "\033[1m"
    _RESET_COLOR = "\033[0m"
    
    class _Colors:
        RED = 1
        GREEN = 2

    _COLORS_BY_LEVEL = {
        "INFO": _Colors.GREEN,
        "ERROR": _Colors.RED
    }

    def _color(self, s, color, bold=False):
        start = self._START_NORMAL
        if bold:
            start += self._START_BOLD

        return start % (30 + color) + s + self._RESET_COLOR

    def format(self, record):
        levelname = record.levelname
        if levelname in self._COLORS_BY_LEVEL:
            record.msg = self._color(
                record.msg,
                self._COLORS_BY_LEVEL[levelname]
            )
        return logging.Formatter.format(self, record)

class GumbyPythonLoggingObserver(PythonLoggingObserver):
    """
    PythonLoggingObserver that uses loggers based on originating modules.
    """
    def emit(self, eventDict):
        if 'logLevel' in eventDict:
            level = eventDict['logLevel']
        elif eventDict['isError']:
            level = logging.ERROR
        else:
            level = logging.INFO
        text = textFromEventDict(eventDict)
        if text is None:
            return

        # get logger based on caller
        frame = inspect.stack()[3][0]
        module = inspect.getmodule(frame).__name__
        logger = logging.getLogger(module)

        logger.log(level, text)
