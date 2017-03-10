#!/usr/bin/env python2
# bartercast_client.py ---
#
# Filename: hidden_services_module.py
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
from twisted.internet import reactor
from posix import environ
from time import sleep

from Tribler.community.tunnel.tunnel_community import TunnelSettings
from Tribler.community.tunnel.crypto.tunnelcrypto import NoTunnelCrypto
from Tribler.community.tunnel.hidden_community import HiddenTunnelCommunity
from Tribler.Core.DownloadConfig import DefaultDownloadStartupConfig
from Tribler.Core.TorrentDef import TorrentDef
from Tribler.dispersy.candidate import Candidate

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module
from gumby.modules.community_experiment_module import CommunityExperimentModule


@static_module
class HiddenServicesModule(CommunityExperimentModule):

    def __init__(self, experiment):
        super(HiddenServicesModule, self).__init__(experiment, HiddenTunnelCommunity)
        self.session_config.set_tunnel_community_socks5_listen_ports(
            [23000 + 100 * self.my_id + i for i in range(5)])
        self.session_config.set_tunnel_community_exitnode_enabled(False)

        self.community_launcher.community_kwargs["settings"] = TunnelSettings(self.session_config)

        self.speed_download = {'download': 0}
        self.speed_upload = {'upload': 0}
        self.progress = {'progress': 0}
        self.total_peers = 20
        self.test_file_size = 100 * 1024 * 1024

    def on_community_loaded(self):
        def monitor_downloads(dslist):
            self.community.monitor_downloads(dslist)
            return 1.0, []
        self.session.set_download_states_callback(monitor_downloads, False)

    @property
    def tunnel_settings(self):
        return self.community_launcher.community_kwargs["settings"]

    @experiment_callback
    def should_become_exit(self, value):
        value = HiddenServicesModule.str2bool(value)
        self.session_config.set_tunnel_community_exitnode_enabled(value)
        self._logger.error("This peer is exit node: %s" % ('Yes' if value else 'No'))

    @experiment_callback
    def enable_security_limiters(self):
        self.tunnel_settings.max_traffic = 1024 * 1024 * 1024 * 1024

    @experiment_callback
    def set_test_file_size(self, filesize):
        self.test_file_size = int(filesize)

    @experiment_callback
    def disable_crypto(self):
        self.tunnel_settings.crypto = NoTunnelCrypto()
        self._logger.error("Crypto on tunnels: Disabled")

    @experiment_callback
    def introduce_candidates(self):
        for port in range(12000, 12000 + self.total_peers):
            if self.dispersy_provider.dispersy_port != port:
                self.community.add_discovered_candidate(Candidate((self.dispersy.wan_address[0], port),
                                                                   tunnel=False))

    @experiment_callback
    def start_download(self, filename, hops=1):
        hops = int(hops)
        self._logger.info('start downloading %d hop(s)' % hops)
        default_dl_config = DefaultDownloadStartupConfig.getInstance()
        dscfg = default_dl_config.copy()
        dscfg.set_hops(hops)
        dscfg.set_dest_dir(path.join(environ["TRIBLER_DIR"], 'download-%s-%d' % (self.session.get_dispersy_port(), hops)))

        def cb_start_download():
            from Tribler.Core.simpledefs import dlstatus_strings
            tdef = self.create_test_torrent(filename)

            def cb(ds):
                self._logger.error('Download infohash=%s, hops=%d, down=%s, up=%d, progress=%s, status=%s, peers=%s, cand=%d' %
                              (tdef.get_infohash().encode('hex')[:5],
                               hops,
                               ds.get_current_speed('down'),
                               ds.get_current_speed('up'),
                               ds.get_progress(),
                               dlstatus_strings[ds.get_status()],
                               sum(ds.get_num_seeds_peers()),
                               sum(1 for _ in self.community.dispersy_yield_verified_candidates())))

                self.log_progress_stats(ds)

                return 1.0, False

            download = self.session.start_download(tdef, dscfg)
            download.set_state_callback(cb, delay=1)

            # Force lookup
            sleep(10)
            self._logger.error("Do a manual dht lookup call to bootstrap it a bit")
            self.community.do_dht_lookup(tdef.get_infohash())

        self.session.lm.threadpool.call_in_thread(0, cb_start_download)

    @experiment_callback
    def setup_seeder(self, filename, hops):
        hops = int(hops)
        self._logger.info('start seeding %d hop(s)' % hops)

        def cb_seeder_download():
            tdef = self.create_test_torrent(filename)

            self._logger.error("Start seeding")

            default_dl_config = DefaultDownloadStartupConfig.getInstance()
            dscfg = default_dl_config.copy()
            dscfg.set_dest_dir(environ["TRIBLER_DIR"])
            dscfg.set_hops(hops)

            def cb(ds):
                from Tribler.Core.simpledefs import dlstatus_strings
                self._logger.error('Seed infohash=%s, hops=%d, down=%d, up=%d, progress=%s, status=%s, peers=%s, cand=%d' %
                              (tdef.get_infohash().encode('hex')[:5],
                               hops,
                               ds.get_current_speed('down'),
                               ds.get_current_speed('up'),
                               ds.get_progress(),
                               dlstatus_strings[ds.get_status()],
                               sum(ds.get_num_seeds_peers()),
                               sum(1 for _ in self.community.dispersy_yield_verified_candidates())))

                self.log_progress_stats(ds)

                return 1.0, False

            download = self.session.start_download(tdef, dscfg)
            download.set_state_callback(cb, delay=1)

        self._logger.error("Call to cb_seeder_download")
        reactor.callInThread(cb_seeder_download)

    def log_progress_stats(self, ds):
        new_speed_download = {'download': ds.get_current_speed('down')}
        self.speed_download = self.print_dict_changes("speed-download", self.speed_download, new_speed_download)

        new_progress = {'progress': ds.get_progress() * 100}
        self.progress = self.print_dict_changes("progress-percentage", self.progress, new_progress)

        new_speed_upload = {'upload': ds.get_current_speed('up')}
        self.speed_upload = self.print_dict_changes("speed-upload", self.speed_upload, new_speed_upload)

    def create_test_torrent(self, filename=''):
        self._logger.error("Create %s download" % filename)
        filename = path.join(environ["TRIBLER_DIR"], path.basename(environ["SCENARIO_FILE"]) + str(filename))
        self._logger.info("Creating torrent..")
        with open(filename, 'wb') as fp:
            fp.write("0" * self.test_file_size)

        self._logger.error("Create a torrent")
        tdef = TorrentDef()
        tdef.add_content(filename)
        tdef.set_tracker("http://fake.net/announce")
        tdef.finalize()
        tdef_file = path.join(environ["OUTPUT_DIR"], "gen.torrent")
        tdef.save(tdef_file)
        return tdef
