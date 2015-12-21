#!/usr/bin/env python2
#
from sys import argv, exit
from os import getpid
from getpass import getuser
from hashlib import md5
from time import time

from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor


class ConfigClientProtocol(LineReceiver):
    def connectionMade(self):
        self.state = 1
        self.sendLine("TIME "+str(time()))

    def lineReceived(self, data):
        username = getuser()
        if self.state == 1:
            data = data.strip()
            id, ip, port, start_timestamp = data.split()
            self.my_id = "%05d" % int(id)
            f = open("/local/%s/dispersy/peer_%s.conf" %(username, self.my_id), "w")
            print >> f, data
            f.close()
            
            self.full_config_file = open("/local/%s/dispersy/peers_%s.conf" %(username, self.my_id), "w")
            
            print self.my_id, start_timestamp
            self.state = 2
            
        elif self.state == 2:
            if data != "END":
                print >> self.full_config_file, data
            else:
                self.full_config_file.close()
                self.transport.loseConnection()
                reactor.stop()

class ConfigClientFactory(ClientFactory):
    def buildProtocol(self, addr):
        return ConfigClientProtocol()

def main():
    sync_server = argv[1]
    if len(argv) > 2:
        server_port = int(argv[2])
    else:
        # determine port based on the process owner's username
        md5sum = md5()
        md5sum.update(getuser())
        server_port = int(md5sum.hexdigest()[-16:], 16) % 20000 + 15000
    
    reactor.connectTCP(sync_server, server_port, ConfigClientFactory())
    reactor.run()

if __name__ == '__main__':
    if len(argv) < 2:
        print "Usage: ./config_sync_client.py <sync_server> (<sync port>)"
        exit(1)
    main()