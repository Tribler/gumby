import binascii
import glob
import os
import random
from asyncio import ensure_future, sleep
from pathlib import Path
from random import Random

from pony.orm import db_session

from tribler_common.simpledefs import dlstatus_strings

from tribler_core.modules.libtorrent.download_config import DownloadConfig
from tribler_core.modules.libtorrent.torrentdef import TorrentDef
from tribler_core.utilities.unicode import hexlify

from gumby.experiment import experiment_callback
from gumby.gumby_tribler_config import GumbyTriblerConfig
from gumby.modules.base_ipv8_module import BaseIPv8Module
from gumby.modules.experiment_module import static_module
from gumby.modules.gumby_session import GumbyTriblerSession
from gumby.modules.ipv8_community_launchers import DHTCommunityLauncher
from gumby.modules.tribler_community_launchers import BandwidthCommunityLauncher, GigaChannelCommunityLauncher, \
    PopularityCommunityLauncher, TriblerTunnelCommunityLauncher
from gumby.util import run_task


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

    def create_ipv8_community_loader(self):
        loader = super().create_ipv8_community_loader()
        loader.set_launcher(TriblerTunnelCommunityLauncher())
        loader.set_launcher(PopularityCommunityLauncher())
        loader.set_launcher(DHTCommunityLauncher())
        loader.set_launcher(GigaChannelCommunityLauncher())
        loader.set_launcher(BandwidthCommunityLauncher())
        return loader

    @experiment_callback
    async def start_session(self):
        self.session = GumbyTriblerSession(config=self.tribler_config)
        self.tribler_config = None

        self._logger.error("Starting Tribler Session")

        if self.custom_ipv8_community_loader:
            self.session.ipv8_community_loader = self.custom_ipv8_community_loader

        await self.session.start()
        self._logger.error("Tribler Session started")
        self.ipv8 = self.session.ipv8
        self.ipv8_available.set_result(self.ipv8)

    @experiment_callback
    def stop_session(self):
        ensure_future(self.session.shutdown())

        # Write away the start time of the experiment
        with open('start_time.txt', 'w') as start_time_time:
            start_time_time.write("%f" % self.experiment.scenario_runner.exp_start_time)

    def setup_config(self):
        if self.ipv8_port is None:
            self.ipv8_port = 12000 + self.experiment.my_id
        self._logger.info("IPv8 port set to %d", self.ipv8_port)

        my_state_path = os.path.join(os.environ['OUTPUT_DIR'], str(self.my_id))
        self._logger.info("State path: %s", my_state_path)

        config = GumbyTriblerConfig(state_dir=Path(my_state_path))
        config.ipv8.bootstrap_override = "0.0.0.0:0"
        config.trustchain.ec_keypair_filename = os.path.join(my_state_path, "tc_keypair_" + str(self.experiment.my_id))
        config.torrent_checking.enabled = False
        config.ipv8.discovery.enabled = False
        config.chant.enabled = False
        config.libtorrent.enabled = False
        config.api.http_enabled = False
        config.libtorrent.port = 20000 + self.experiment.my_id * 10
        config.ipv8.port = self.ipv8_port
        config.tunnel_community.enabled = False
        config.dht.enabled = False
        config.general.version_checker_enabled = False
        config.bootstrap.enabled = False
        config.popularity_community.enabled = False
        return config

    @experiment_callback
    def set_transfer_size(self, size):
        self.transfer_size = int(size)

    @experiment_callback
    def set_libtorrentmgr_alert_mask(self, mask=0xffffffff):
        self.session.dlmgr.default_alert_mask = mask
        self.session.dlmgr.session_stats_callback = self._process_libtorrent_alert
        for ltsession in self.session.dlmgr.ltsessions.values():
            ltsession.set_alert_mask(mask)

    def _process_libtorrent_alert(self, alert):
        self._logger.info("LibtorrentDownloadImpl: alert %s", alert)

    @experiment_callback
    def enable_bootstrap_download(self):
        self.tribler_config.bootstrap.enabled = True
        self.tribler_config.libtorrent.enabled = True

    @experiment_callback
    def setup_initial_bootstrap_seeder(self):
        bootstrap_dir = self.tribler_config.state_dir / 'bootstrap'
        if not bootstrap_dir.exists():
            os.mkdir(bootstrap_dir)
        file_name = bootstrap_dir / 'bootstrap.block'
        bootstrap_size = 25
        seed = 42
        random.seed(seed)
        if not file_name.exists():
            with open(file_name, 'wb') as fp:
                fp.write(bytearray(random.getrandbits(8) for _ in range(bootstrap_size * 1024 * 1024)))

    @experiment_callback
    def start_bootstrap_download(self):
        self.session.start_bootstrap_download()

    @experiment_callback
    def disable_lt_rc4_encryption(self):
        """
        Disable the RC4 encryption that the libtorrent session in Tribler uses by default.
        This should speed up downloads when testing.
        """
        ltsession = self.session.dlmgr.get_session(0)
        settings = self.session.dlmgr.get_session_settings(ltsession)
        settings['prefer_rc4'] = False
        self.session.dlmgr.set_session_settings(ltsession, settings)

    @experiment_callback
    async def transfer(self, action="download", hops=None, timeout=None, download_id=None, length=None):
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

        file_name = os.path.basename(os.environ["SCENARIO_FILE"])
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
        dscfg = DownloadConfig(state_dir=self.session.config.state_dir)
        if hops is not None:
            dscfg.set_hops(hops)
        dscfg.set_dest_dir(os.path.join(os.environ["OUTPUT_DIR"], str(self.my_id)))
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

        download = self.session.dlmgr.start_download(tdef=tdef, config=dscfg)
        download.set_state_callback(cb)

        if action == 'download':
            # Schedule a DHT lookup to fetch peers to add to this download
            await sleep(5)
            peers = await self.session.dht_community.find_values(tdef.get_infohash())
            if not peers:
                self._logger.info("No DHT peer found for infohash!")
            else:
                for peer in peers:
                    parts = peer[0].split(b":")
                    download.add_peer((parts[0], int(parts[1])))
        elif action == 'seed':
            host, _ = self.experiment.get_peer_ip_port_by_id(str(self.experiment.my_id))
            value = "%s:%d" % (host, self.session.config.libtorrent.port)
            await self.session.dht_community.store_value(tdef.get_infohash(), value.encode('utf-8'))

        if timeout:
            run_task(self.session.dlmgr.remove_download, download, True, delay=timeout)

    @experiment_callback
    def create_channel(self):
        self.session.mds.ChannelMetadata.create_channel('test' + ''.join(str(i) for i in range(100)), 'test')

    @experiment_callback
    def add_torrents_to_channel(self, amount):
        amount = int(amount)

        with db_session:
            my_channel = self.session.mds.ChannelMetadata.get_my_channel()
            for ind in range(amount):
                test_tdef = self.create_test_torrent("file%s.txt" % ind, 0, 1024)
                my_channel.add_torrent_to_channel(test_tdef)

            torrent_dict = my_channel.commit_channel_torrent()
            if torrent_dict:
                self.session.gigachannel_manager.updated_my_channel(TorrentDef.load_from_dict(torrent_dict))

    @experiment_callback
    def add_peer_to_downloads(self, peer_nr):
        self._logger.info("Adding peer %s to all downloads", peer_nr)
        host, port = self.experiment.get_peer_ip_port_by_id(peer_nr)
        for download in self.session.get_downloads():
            download.add_peer((host, port))

    @experiment_callback
    def remove_download_data(self):
        for f in glob.glob(os.environ["SCENARIO_FILE"] + "*"):
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
