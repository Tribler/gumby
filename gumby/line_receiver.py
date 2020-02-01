import logging
from asyncio import DatagramProtocol


class LineReceiver(DatagramProtocol):
    _buffer = b''
    _busy = False
    delimiter = b'\r\n'
    MAX_LENGTH = 16384

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        if self._busy:
            self._buffer += data
            return

        try:
            self._busy = True
            self._buffer += data
            while self._buffer:
                try:
                    line, self._buffer = self._buffer.split(self.delimiter, 1)
                except ValueError:
                    if len(self._buffer) >= (self.MAX_LENGTH + len(self.delimiter)):
                        line, self._buffer = self._buffer, b''
                        return self.line_length_exceeded(line)
                    return
                else:
                    lineLength = len(line)
                    if lineLength > self.MAX_LENGTH:
                        exceeded = line + self.delimiter + self._buffer
                        self._buffer = b''
                        return self.line_length_exceeded(exceeded)
                    why = self.line_received(line)
                    if (why or self.transport and self.transport.is_closing()):
                        return why
        finally:
            self._busy = False

    def line_received(self, line):
        raise NotImplementedError

    def send_line(self, line):
        return self.transport.write(line + self.delimiter)

    def line_length_exceeded(self, _):
        return self.transport.lose_connection()

    def eof_received(self):
        return False
