import glob
import os
import random

from posix import environ
from random import Random

import binascii
from pony.orm import db_session
from twisted.internet import reactor

from six.moves import xrange

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module
from gumby.modules.base_ipv8_module import BaseIPv8Module

from ipv8.dht.provider import DHTCommunityProvider

from Tribler.Core.Config.download_config import DownloadConfig
from Tribler.Core.Utilities.unicode import hexlify
from Tribler.Core.simpledefs import dlstatus_strings
from Tribler.Core.TorrentDef import TorrentDef

try:
    long  # Python 2
except NameError:  # Python 3
    long = int  # pylint: disable=redefined-builtin


@static_module
class TriblerModule(BaseIPv8Module):

    def __init__(self, experiment):
        super(TriblerModule, self).__init__(experiment)
        self.transfer_size = 25 * 1024 * 1024
        self.ipv8 = None
        self.download_stats = {
            'download': 0,
            'progress': 0.0,
            'upload': 0
        }
        self.dht_provider = None

    @experiment_callback
    def start_session(self):
        super(TriblerModule, self).start_session()

        self._logger.error("Starting Tribler Session")

        if self.custom_ipv8_community_loader:
            self.session.lm.ipv8_community_loader = self.custom_ipv8_community_loader

        def on_tribler_started(_):
            self._logger.error("Tribler Session started")
            self.ipv8 = self.session.lm.ipv8
            self.dht_provider = DHTCommunityProvider(self.session.lm.dht_community,
                                                     self.session.config.get_libtorrent_port())
            self.ipv8_available.callback(self.ipv8)

        return self.session.start().addCallback(on_tribler_started)

    @experiment_callback
    def stop_session(self):
        reactor.callFromThread(self.session.shutdown)

        # Write away the start time of the experiment
        with open('start_time.txt', 'w') as start_time_time:
            start_time_time.write("%f" % self.experiment.scenario_runner.exp_start_time)

    @experiment_callback
    def set_transfer_size(self, size):
        self.transfer_size = long(size)

    @experiment_callback
    def set_libtorrentmgr_alert_mask(self, mask=0xffffffff):
        self.session.lm.ltmgr.default_alert_mask = mask
        self.session.lm.ltmgr.alert_callback = self._process_libtorrent_alert
        for ltsession in self.session.lm.ltmgr.ltsessions.values():
            ltsession.set_alert_mask(mask)

    @experiment_callback
    def enable_bootstrap_download(self):
        self.tribler_config.set_bootstrap_enabled(True)
        self.tribler_config.set_libtorrent_enabled(True)

    @experiment_callback
    def setup_initial_bootstrap_seeder(self):
        bootstrap_dir = os.path.join(self.tribler_config.get_state_dir(), 'bootstrap')
        if not os.path.exists(bootstrap_dir):
            os.mkdir(bootstrap_dir)
        file_name = os.path.join(bootstrap_dir, 'bootstrap.block')
        bootstrap_size = 25
        seed = 42
        random.seed(seed)
        if not os.path.exists(file_name):
            with open(file_name, 'wb') as fp:
                fp.write(bytearray(random.getrandbits(8) for _ in xrange(bootstrap_size * 1024 * 1024)))

    @experiment_callback
    def start_bootstrap_download(self):
        self.session.lm.start_bootstrap_download()

    @experiment_callback
    def disable_lt_rc4_encryption(self):
        """
        Disable the RC4 encryption that the libtorrent session in Tribler uses by default.
        This should speed up downloads when testing.
        """
        ltsession = self.session.lm.ltmgr.get_session(0)
        settings = ltsession.get_settings()
        settings['prefer_rc4'] = False
        ltsession.set_settings(settings)

    @experiment_callback
    def transfer(self, action="download", hops=None, timeout=None, download_id=None, length=None):
        """
        Start to seed/download a specific torrent file. After starting the download, it will either announce itself
        in the DHT (when seeding) or look for peers (when downloading)

        :param action: Whether to seed or download a torrent (either 'seed' or 'download')
        :param hops: The number of hops to download/seed with
        :param timeout: A timeout for this download (it will be removed when the timeout is triggered)
        :param download_id: An identifier for the download, will be used to generate a unique download
        :param length: The size of the download, defaults to self.transfer_size
        """
        assert action in ("download", "seed"), "Invalid transfer kind"

        file_name = os.path.basename(environ["SCENARIO_FILE"])
        if download_id:
            download_id = int(download_id)
        else:
            download_id = self.experiment.server_vars["global_random"]

        file_name += str(download_id)

        if hops is not None:
            hops = int(hops)
            self._logger.info('Start transfer: %s file "%s" with %d hop(s)', action, file_name, hops)
        else:
            self._logger.info('Start transfer: %s file "%s"', action, file_name)

        if length:
            length = int(length)
        else:
            length = self.transfer_size

        tdef = self.create_test_torrent(file_name, download_id, length)
        dscfg = DownloadConfig(state_dir=self.session.config.get_state_dir())
        if hops is not None:
            dscfg.set_hops(hops)
        dscfg.set_dest_dir(os.path.join(environ["OUTPUT_DIR"], str(self.my_id)))
        if action == "download":
            os.remove(os.path.join(dscfg.get_dest_dir(), file_name))

        def cb(ds):
            self._logger.info('transfer: %s infohash=%s, hops=%d, down=%d, up=%d, progress=%s, status=%s, seeds=%s',
                              action,
                              hexlify(tdef.get_infohash())[:5],
                              hops if hops else 0,
                              ds.get_current_speed('down'),
                              ds.get_current_speed('up'),
                              ds.get_progress(),
                              dlstatus_strings[ds.get_status()],
                              sum(ds.get_num_seeds_peers()))

            if ds.get_peerlist():
                for peer in ds.get_peerlist():
                    self._logger.info(" - peer %s, client %s, addr %s:%s has (%s), U: %s D: %s",
                                      peer["id"],
                                      peer["extended_version"],
                                      peer["ip"],
                                      peer["port"],
                                      peer["completed"] * 100.0,
                                      peer["uprate"],
                                      peer["downrate"])

            new_download_stats = {
                'download': ds.get_current_speed('down'),
                'progress': ds.get_progress() * 100,
                'upload': ds.get_current_speed('up')
            }
            self.download_stats = self.print_dict_changes("download-stats", self.download_stats, new_download_stats)

            return 1.0

        download = self.session.start_download_from_tdef(tdef, dscfg)
        download.set_state_callback(cb)

        if action == 'download':
            # Schedule a DHT lookup to fetch peers to add to this download
            def on_peers(info):
                _, peers, _ = info
                self._logger.debug("Received peers for seeder lookup: %s", str(peers))
                for peer in peers:
                    download.add_peer(peer)

            reactor.callLater(5, self.dht_provider.lookup, tdef.get_infohash(), on_peers)

        if timeout:
            reactor.callLater(long(timeout), self.session.remove_download_by_id, tdef.infohash, remove_content=True,
                              remove_state=True)

    @experiment_callback
    def create_channel(self):
        self.session.lm.mds.ChannelMetadata.create_channel('test' + ''.join(str(i) for i in range(100)), 'test')

    @experiment_callback
    def add_torrents_to_channel(self, amount):
        amount = int(amount)

        with db_session:
            my_channel = self.session.lm.mds.ChannelMetadata.get_my_channel()
            for ind in xrange(amount):
                test_tdef = self.create_test_torrent("file%s.txt" % ind, 0, 1024)
                my_channel.add_torrent_to_channel(test_tdef)

            torrent_dict = my_channel.commit_channel_torrent()
            if torrent_dict:
                self.session.lm.gigachannel_manager.updated_my_channel(TorrentDef.load_from_dict(torrent_dict))

    @experiment_callback
    def add_peer_to_downloads(self, peer_nr):
        self._logger.info("Adding peer %s to all downloads", peer_nr)
        host, port = self.experiment.get_peer_ip_port_by_id(peer_nr)
        for download in self.session.get_downloads():
            download.add_peer((host, port))

    @experiment_callback
    def remove_download_data(self):
        for f in glob.glob(environ["SCENARIO_FILE"] + "*"):
            os.remove(f)

    @staticmethod
    def int2bytes(i):
        hex_string = '%x' % i
        n = len(hex_string)
        return binascii.unhexlify(hex_string.zfill(n + (n & 1)))

    def create_test_torrent(self, file_name, download_id, length):
        if not os.path.exists(file_name):
            self._logger.info("Creating torrent data file %s", file_name)
            with open(file_name, 'wb') as fp:
                rand = Random()
                rand.seed(download_id)
                fp.write(TriblerModule.int2bytes(rand.getrandbits(8 * length)))

        tdef = TorrentDef()
        tdef.add_content(file_name)
        tdef.save()
        return tdef

    def _process_libtorrent_alert(self, alert):
        self._logger.info("LibtorrentDownloadImpl: alert %s", alert)

    @experiment_callback
    def write_overlay_statistics(self):
        """
        Write information about the IPv8 overlay networks to a file.
        """
        with open('overlays.txt', 'w') as overlays_file:
            overlays_file.write("name,pub_key,peers\n")
            for overlay in self.session.lm.ipv8.overlays:
                overlays_file.write("%s,%s,%d\n" % (overlay.__class__.__name__,
                                                    hexlify(overlay.my_peer.public_key.key_to_bin()),
                                                    len(overlay.get_peers())))

        # Write verified peers
        with open('verified_peers.txt', 'w') as peers_file:
            for peer in self.session.lm.ipv8.network.verified_peers:
                peers_file.write('%d\n' % (peer.address[1] - 12000))

        # Write bandwidth statistics
        with open('bandwidth.txt', 'w') as bandwidth_file:
            bandwidth_file.write("%d,%d" % (self.session.lm.ipv8.endpoint.bytes_up,
                                            self.session.lm.ipv8.endpoint.bytes_down))

    @experiment_callback
    def write_download_statistics(self):
        """
        Write away information about the downloads in Tribler.
        """
        with open('downloads.txt', 'w') as downloads_file:
            downloads_file.write('infohash,status,progress\n')
            for download in self.session.get_downloads():
                state = download.get_state()
                downloads_file.write("%s,%s,%f\n" % (
                    hexlify(download.get_def().get_infohash()),
                    dlstatus_strings[state.get_status()],
                    state.get_progress()))
