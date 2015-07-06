#!/usr/bin/env python
# bartercast_client.py ---
#
# Filename: hiddenservices_client.py
# Description:
# Author: Rob Ruigrok
# Maintainer:
# Created: Wed Apr 22 11:44:23 2015 (+0200)

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

from os import path

from gumby.experiments.TriblerDispersyClient import TriblerDispersyExperimentScriptClient,\
    BASE_DIR
from gumby.experiments.dispersyclient import main
import logging
from twisted.internet import reactor
from posix import environ
from time import sleep


class HiddenServicesClient(TriblerDispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.tunnel.hidden_community import HiddenTunnelCommunity
        TriblerDispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = HiddenTunnelCommunity
        self.speed_download = {'download': 0}
        self.speed_upload = {'upload': 0}
        self.progress = {'progress': 0}
        self.totalpeers = 20
        self.testfilesize = 100 * 1024 * 1024
        self.security_limiters = False

    def init_community(self, become_exitnode=None, no_crypto=None):
        become_exitnode = become_exitnode == 'exit'
        no_crypto = no_crypto == 'no_crypto'

        from Tribler.community.tunnel.tunnel_community import TunnelSettings
        tunnel_settings = TunnelSettings()

        tunnel_settings.become_exitnode = become_exitnode
        logging.error("This peer is exit node: %s" % ('Yes' if become_exitnode else 'No'))

        tunnel_settings.socks_listen_ports = [23000 + (10 * self.scenario_runner._peernumber) + i for i in range(5)]

        if not self.security_limiters:
            tunnel_settings.max_traffic = 1024 * 1024 * 1024 * 1024

        tunnel_settings.min_circuits = 3
        tunnel_settings.max_circuits = 5

        logging.error("My wan address is %s" % repr(self._dispersy._wan_address[0]))

        logging.error("Crypto on tunnels: %s" % ('Disabled' if no_crypto else 'Enabled'))
        if no_crypto:
            from Tribler.community.tunnel.crypto.tunnelcrypto import NoTunnelCrypto
            tunnel_settings.crypto = NoTunnelCrypto()

        self.set_community_kwarg('tribler_session', self.session)
        self.set_community_kwarg('settings', tunnel_settings)

    def get_my_member(self):
        return self._dispersy.get_new_member(u"curve25519")

    def log_progress_stats(self, ds):
        new_speed_download = {'download': ds.get_current_speed('down')}
        self.speed_download = self.print_on_change("speed-download",
                                                   self.speed_download,
                                                   new_speed_download)

        new_progress = {'progress': ds.get_progress() * 100}
        self.progress = self.print_on_change("progress-percentage",
                                             self.progress,
                                             new_progress)

        new_speed_upload = {'upload': ds.get_current_speed('up')}
        self.speed_upload = self.print_on_change("speed-upload",
                                                 self.speed_upload,
                                                 new_speed_upload)

    def fake_create_introduction_point(self, info_hash):
        logging.error("Fake creating introduction points, to prevent this download from messing other experiments")
        pass

    def start_download(self, filename, hops=1):
        hops = int(hops)
        self.annotate('start downloading %d hop(s)' % hops)
        from Tribler.Main.globals import DefaultDownloadStartupConfig
        defaultDLConfig = DefaultDownloadStartupConfig.getInstance()
        dscfg = defaultDLConfig.copy()
        dscfg.set_hops(hops)
        dscfg.set_dest_dir(path.join(BASE_DIR, 'tribler', 'download-%s-%d' % (self.session.get_dispersy_port(), hops)))

        # Monkeypatch! Disable creating intropoints after finishing downloading
        self._community.create_introduction_point = self.fake_create_introduction_point

        def cb_start_download():
            from Tribler.Core.simpledefs import dlstatus_strings
            tdef = self.create_test_torrent(filename)

            def cb(ds):
                logging.error('Download infohash=%s, hops=%d, down=%s, up=%d, progress=%s, status=%s, peers=%s, cand=%d' %
                              (tdef.get_infohash().encode('hex')[:5],
                               hops,
                               ds.get_current_speed('down'),
                               ds.get_current_speed('up'),
                               ds.get_progress(),
                               dlstatus_strings[ds.get_status()],
                               sum(ds.get_num_seeds_peers()),
                               sum(1 for _ in self._community.dispersy_yield_verified_candidates())))

                self.log_progress_stats(ds)

                return 1.0, False

            download = self.session.start_download(tdef, dscfg)
            download.set_state_callback(cb, delay=1)

            # Force lookup
            sleep(10)
            logging.error("Do a manual dht lookup call to bootstrap it a bit")
            self._community.do_dht_lookup(tdef.get_infohash())

        self.session.lm.threadpool.call_in_thread(0, cb_start_download)

    def online(self, dont_empty=False):
        TriblerDispersyExperimentScriptClient.online(self, dont_empty)
        self.session.set_anon_proxy_settings(2, ("127.0.0.1", self.session.get_tunnel_community_socks5_listen_ports()))

        def monitor_downloads(dslist):
            self._community.monitor_downloads(dslist)
            return (1.0, [])
        self.session.set_download_states_callback(monitor_downloads, False)

    def introduce_candidates(self):
        # We are letting dispersy deal with addins the community's candidate to itself.
        from Tribler.dispersy.candidate import Candidate
        for port in range(21000, 21000 + self.totalpeers):
            if self.dispersy_port != port:
                self._community.add_discovered_candidate(Candidate((self._dispersy._wan_address[0], port),
                                                                   tunnel=False))

    def create_test_torrent(self, filename=''):
        logging.error("Create %s download" % filename)
        filename = path.join(BASE_DIR, "tribler", str(self.scenario_file) + str(filename))
        logging.info("Creating torrent..")
        with open(filename, 'wb') as fp:
            fp.write("0" * self.testfilesize)

        logging.error("Create a torrent")
        from Tribler.Core.TorrentDef import TorrentDef
        tdef = TorrentDef()
        tdef.add_content(filename)
        tdef.set_tracker("http://fake.net/announce")
        tdef.finalize()
        tdef_file = path.join(BASE_DIR, "output", "gen.torrent")
        tdef.save(tdef_file)
        return tdef

    def set_test_file_size(self, filesize):
        self.testfilesize = int(filesize)

    def set_security_limiters(self, value):
        self.security_limiters = value == 'True'

    def setup_seeder(self, filename, hops):
        hops = int(hops)
        self.annotate('start seeding %d hop(s)' % hops)

        def cb_seeder_download():
            tdef = self.create_test_torrent(filename)

            logging.error("Start seeding")

            from Tribler.Main.globals import DefaultDownloadStartupConfig
            defaultDLConfig = DefaultDownloadStartupConfig.getInstance()
            dscfg = defaultDLConfig.copy()
            dscfg.set_dest_dir(path.join(BASE_DIR, "tribler"))
            dscfg.set_hops(hops)

            def cb(ds):
                from Tribler.Core.simpledefs import dlstatus_strings
                logging.error('Seed infohash=%s, hops=%d, down=%d, up=%d, progress=%s, status=%s, peers=%s, cand=%d' %
                              (tdef.get_infohash().encode('hex')[:5],
                               hops,
                               ds.get_current_speed('down'),
                               ds.get_current_speed('up'),
                               ds.get_progress(),
                               dlstatus_strings[ds.get_status()],
                               sum(ds.get_num_seeds_peers()),
                               sum(1 for _ in self._community.dispersy_yield_verified_candidates())))

                self.log_progress_stats(ds)

                return 1.0, False

            download = self.session.start_download(tdef, dscfg)
            download.set_state_callback(cb, delay=1)

        logging.error("Call to cb_seeder_download")
        reactor.callInThread(cb_seeder_download)

    def registerCallbacks(self):
        TriblerDispersyExperimentScriptClient.registerCallbacks(self)
        self.scenario_runner.register(self.setup_seeder, 'setup_seeder')
        self.scenario_runner.register(self.start_download, 'start_download')
        self.scenario_runner.register(self.init_community, 'init_community')
        self.scenario_runner.register(self.set_test_file_size, 'set_test_file_size')
        self.scenario_runner.register(self.set_security_limiters, 'set_security_limiters')
        self.scenario_runner.register(self.introduce_candidates, 'introduce_candidates')

if __name__ == '__main__':
    HiddenServicesClient.scenario_file = environ.get('SCENARIO_FILE', 'hiddenservices-1-hop-seeder.scenario')
    main(HiddenServicesClient)
