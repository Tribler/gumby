import decimal
import logging
import re

import pexpect
from twisted.web import resource, http


MAX_MINT = 10 ** 19  # 10 trillion libras


class FaucetEndpoint(resource.Resource):

    def __init__(self, client):
        resource.Resource.__init__(self)
        self.client = client
        self._logger = logging.getLogger(self.__class__.__name__)

    def getChild(self, path, request):
        if not path:
            return self

    def render_POST(self, request):
        address = request.args[b'address'][0].decode()
        self._logger.info("Received mint request for address %s", address)
        if re.match('^[a-f0-9]{64}$', address) is None:
            request.setResponseCode(http.BAD_REQUEST)
            return b"Malformed address"

        try:
            amount = decimal.Decimal(request.args[b'amount'][0].decode())
        except decimal.InvalidOperation:
            request.setResponseCode(http.BAD_REQUEST)
            return b"Bad amount"

        if amount > MAX_MINT:
            request.setResponseCode(http.BAD_REQUEST)
            return b'Exceeded max amount of {}'.format(MAX_MINT / (10 ** 6)), 400

        try:
            self.client.sendline("a m {} {}".format(address, amount / (10 ** 6)))
            self.client.expect("Mint request submitted", timeout=2)
        except pexpect.exceptions.ExceptionPexpect:
            self.client.terminate(True)
            raise

        return b"done"
