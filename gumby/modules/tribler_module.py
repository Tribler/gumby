import binascii
import glob
import os
import random
import signal
from abc import abstractmethod
from asyncio import ensure_future, sleep
from base64 import b64decode, b64encode
from pathlib import Path

from ipv8.community import Community
from ipv8.dht.community import DHTCommunity
from ipv8.peer import Peer
from ipv8.peerdiscovery.churn import RandomChurn
from ipv8.peerdiscovery.discovery import EdgeWalk, RandomWalk

from ipv8_service import IPv8

from pony.orm import db_session, desc

from tribler_core.components.bandwidth_accounting.bandwidth_accounting_component import BandwidthAccountingComponent
from tribler_core.components.base import Session
from tribler_core.components.gigachannel.gigachannel_component import GigaChannelComponent
from tribler_core.components.gigachannel_manager.gigachannel_manager_component import GigachannelManagerComponent
from tribler_core.components.ipv8.ipv8_component import Ipv8Component
from tribler_core.components.key.key_component import KeyComponent
from tribler_core.components.libtorrent.download_manager.download_config import DownloadConfig
from tribler_core.components.libtorrent.libtorrent_component import LibtorrentComponent
from tribler_core.components.libtorrent.torrentdef import TorrentDef
from tribler_core.components.metadata_store.metadata_store_component import MetadataStoreComponent
from tribler_core.components.payout.payout_component import PayoutComponent
from tribler_core.components.popularity.popularity_component import PopularityComponent
from tribler_core.components.resource_monitor.resource_monitor_component import ResourceMonitorComponent
from tribler_core.components.restapi.restapi_component import RESTComponent
from tribler_core.components.socks_servers.socks_servers_component import SocksServersComponent
from tribler_core.components.tag.tag_component import TagComponent
from tribler_core.components.torrent_checker.torrent_checker_component import TorrentCheckerComponent
from tribler_core.components.tunnel.tunnel_component import TunnelsComponent
from tribler_core.components.watch_folder.watch_folder_component import WatchFolderComponent
from tribler_core.config.tribler_config import TriblerConfig
from tribler_core.config.tribler_config_section import TriblerConfigSection
from tribler_core.utilities.simpledefs import dlstatus_strings
from tribler_core.utilities.unicode import hexlify

from gumby.experiment import experiment_callback
from gumby.modules.base_ipv8_module import IPv8Provider
from gumby.modules.experiment_module import ExperimentModule
from gumby.util import generate_keypair_trustchain, run_task, save_keypair_trustchain, save_pub_key_trustchain


class TagsSettings(TriblerConfigSection):
    enabled: bool = False


class GumbyTriblerConfig(TriblerConfig):
    tags: TagsSettings = TagsSettings()


# pylint: disable=too-many-public-methods
class TriblerModule(IPv8Provider):
    tribler_session: Session
    tribler_config: GumbyTriblerConfig

    def __init__(self, experiment):
        if getattr(experiment, 'tribler_module', None) is not None:
            raise RuntimeError('Cannot use more then one tribler_module in experiment')

        super().__init__(experiment)
        experiment.tribler_module = self

        self.transfer_size = 25 * 1024 * 1024
        self.download_stats = {
            'download': 0,
            'progress': 0.0,
            'upload': 0
        }
        self.overlays_to_isolate = {}
        self.isolated_overlays = set()

    def on_id_received(self):
        super().on_id_received()
        self.tribler_config = self.setup_config()
        setattr(self.experiment, 'tribler_config', self.tribler_config)

    @experiment_callback
    def isolate_ipv8_overlay(self, name):
        if self.isolated_overlays:
            # this check was added as a safety check that the code does not have a race conditions
            raise RuntimeError("Too late attempt to isolate overlays")

        self.overlays_to_isolate.setdefault(name, False)

    @experiment_callback
    def enable_ipv8_statistics(self):
        self.tribler_config.ipv8.statistics = True

    def do_isolate_overlays(self):
        overlay: Community
        for overlay in self.ipv8.overlays:
            name = overlay.__class__.__name__
            if name in self.overlays_to_isolate and not self.overlays_to_isolate[name]:
                overlay.community_id = self.generate_isolated_community_id(overlay)
                self.overlays_to_isolate[name] = True
                self.isolated_overlays.add(overlay)
        for overlay_name, was_isolated in self.overlays_to_isolate.items():
            if not was_isolated:
                raise RuntimeError(f'Overlay {overlay_name} was not isolated')

    def generate_isolated_community_id(self, overlay):
        from ipv8.keyvault.crypto import ECCrypto  # pylint: disable=import-outside-toplevel
        eccrypto = ECCrypto()
        unique_id = (overlay.__class__.__name__ + self.session_id).encode('utf-8')
        private_bin = b"".join([unique_id[i:i+1] if i < len(unique_id) else b"0" for i in range(68)])
        eckey = eccrypto.key_from_private_bin(b"LibNaCLSK:" + private_bin)
        master_peer = Peer(eckey.pub().key_to_bin())
        return master_peer.mid

    def components_gen(self, config: GumbyTriblerConfig):
        """
        Copy-pasted and modified version of tribler_core.start_core.components_gen
        """
        # Removed part of components_gen are commented out and not removed to make the difference clearer

        # yield ReporterComponent()

        if config.api.http_enabled or config.api.https_enabled:
            yield RESTComponent()
        if config.chant.enabled or config.torrent_checking.enabled:
            yield MetadataStoreComponent()
        if config.ipv8.enabled:
            yield Ipv8Component()

        yield KeyComponent()

        if config.tags.enabled:
            yield TagComponent()

        if config.libtorrent.enabled:
            yield LibtorrentComponent()
        if config.ipv8.enabled and config.chant.enabled:
            yield GigaChannelComponent()
        if config.ipv8.enabled:
            yield BandwidthAccountingComponent()
        if config.resource_monitor.enabled:
            yield ResourceMonitorComponent()

        # The components below are skipped if config.gui_test_mode == True
        if config.gui_test_mode:
            return

        if config.libtorrent.enabled:
            yield SocksServersComponent()

        if config.torrent_checking.enabled:
            yield TorrentCheckerComponent()
        if config.ipv8.enabled and config.torrent_checking.enabled and config.popularity_community.enabled:
            yield PopularityComponent()
        if config.ipv8.enabled and config.tunnel_community.enabled:
            yield TunnelsComponent()
        if config.ipv8.enabled:
            yield PayoutComponent()
        if config.watch_folder.enabled:
            yield WatchFolderComponent()
        # if config.general.version_checker_enabled:
        #     yield VersionCheckComponent()
        if config.chant.enabled and config.chant.manager_enabled and config.libtorrent.enabled:
            yield GigachannelManagerComponent()

    @experiment_callback
    async def start_session(self):
        config: GumbyTriblerConfig = self.tribler_config
        self.tribler_config = None
        config.libtorrent.proxy_type = 0
        config.libtorrent.proxy_server = ":"
        components = list(self.components_gen(config))
        session = Session(config, components)
        signal.signal(signal.SIGTERM, lambda signum, stack: session.shutdown_event.set)
        session.set_as_default()
        self.tribler_session = session

        self._logger.info("Starting Tribler Session")
        await session.start_components()
        self._logger.info("Tribler Session started")

        self.ipv8 = Ipv8Component.instance().ipv8
        self.do_isolate_overlays()
        self._logger.info("IPv8 overlay should be isolated now")
        self.ipv8_available.set_result(self.ipv8)

    @experiment_callback
    async def stop_session(self):
        self.tribler_session.shutdown_event.set()
        await self.tribler_session.shutdown()

        # Write away the start time of the experiment
        with open('start_time.txt', 'w') as start_time_time:
            start_time_time.write("%f" % self.experiment.scenario_runner.exp_start_time)

    def setup_config(self) -> GumbyTriblerConfig:
        if self.ipv8_port is None:
            self.ipv8_port = 12000 + self.experiment.my_id
        self._logger.info("IPv8 port set to %d", self.ipv8_port)

        my_state_path = os.path.join(os.environ['OUTPUT_DIR'], str(self.my_id))
        self._logger.info("State path: %s", my_state_path)

        config = GumbyTriblerConfig(state_dir=Path(my_state_path))
        config.general.version_checker_enabled = False
        config.tunnel_community.enabled = False
        config.bootstrap.enabled = False
        config.ipv8.port = self.ipv8_port
        config.ipv8.bootstrap_override = "0.0.0.0:0"
        config.discovery_community.enabled = False
        config.dht.enabled = False
        config.trustchain.ec_keypair_filename = os.path.join(my_state_path, "tc_keypair_" + str(self.experiment.my_id))
        config.chant.enabled = False
        config.torrent_checking.enabled = False
        config.libtorrent.enabled = False
        config.libtorrent.port = 20000 + self.experiment.my_id * 10
        config.api.http_enabled = False
        config.resource_monitor.enabled = False
        config.popularity_community.enabled = False
        config.tags.enabled = False
        return config

    @experiment_callback
    def set_transfer_size(self, size):
        self.transfer_size = int(size)

    @experiment_callback
    def set_libtorrentmgr_alert_mask(self, mask=0xffffffff):
        download_manager = LibtorrentComponent.instance().download_manager
        download_manager.default_alert_mask = mask
        download_manager.session_stats_callback = self._process_libtorrent_alert
        for ltsession in download_manager.ltsessions.values():
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
    def start_bootstrap_download(self):  # obsolete?
        # self.tribler_session.start_bootstrap_download()
        pass

    @experiment_callback
    def disable_lt_rc4_encryption(self):
        """
        Disable the RC4 encryption that the libtorrent session in Tribler uses by default.
        This should speed up downloads when testing.
        """
        download_manager = LibtorrentComponent.instance().download_manager
        ltsession = download_manager.get_session(0)
        settings = download_manager.get_session_settings(ltsession)
        settings['prefer_rc4'] = False
        download_manager.set_session_settings(ltsession, settings)

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
        download_config = DownloadConfig(state_dir=self.tribler_session.config.state_dir)
        if hops is not None:
            download_config.set_hops(hops)
        download_config.set_dest_dir(os.path.join(os.environ["OUTPUT_DIR"], str(self.my_id)))
        if action == "download":
            os.remove(os.path.join(download_config.get_dest_dir(), file_name))

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

        download_manager = LibtorrentComponent.instance().download_manager
        download = download_manager.start_download(tdef=tdef, config=download_config)
        download.set_state_callback(cb)

        dht_community: DHTCommunity = Ipv8Component.instance().ipv8.get_overlay(DHTCommunity)
        if action == 'download':
            # Schedule a DHT lookup to fetch peers to add to this download
            await sleep(5)
            peers = await dht_community.find_values(tdef.get_infohash())
            if not peers:
                self._logger.info("No DHT peer found for infohash!")
            else:
                for peer in peers:
                    parts = peer[0].split(b":")
                    download.add_peer((parts[0], int(parts[1])))
        elif action == 'seed':
            host, _ = self.experiment.get_peer_ip_port_by_id(str(self.experiment.my_id))
            value = "%s:%d" % (host, self.tribler_session.config.libtorrent.port)
            await dht_community.store_value(tdef.get_infohash(), value.encode('utf-8'))

        if timeout:
            run_task(download_manager.remove_download, download, True, delay=timeout)

    @experiment_callback
    def create_channel(self):
        mds = MetadataStoreComponent.instance().mds
        mds.ChannelMetadata.create_channel('test' + ''.join(str(i) for i in range(100)), 'test')

    @experiment_callback
    def add_torrents_to_channel(self, amount):
        amount = int(amount)

        with db_session:
            mds = MetadataStoreComponent.instance().mds
            my_channel = mds.ChannelMetadata.get_my_channels().order_by(lambda c: desc(c.rowid)).first()
            for ind in range(amount):
                test_tdef = self.create_test_torrent("file%s.txt" % ind, 0, 1024)
                my_channel.add_torrent_to_channel(test_tdef)

            torrent_dict = my_channel.commit_channel_torrent()
            if torrent_dict:
                gigachannel_manager = GigachannelManagerComponent.instance().gigachannel_manager
                gigachannel_manager.updated_my_channel(TorrentDef.load_from_dict(torrent_dict))

    @experiment_callback
    def add_peer_to_downloads(self, peer_nr):
        self._logger.info("Adding peer %s to all downloads", peer_nr)
        host, port = self.experiment.get_peer_ip_port_by_id(peer_nr)
        download_manager = LibtorrentComponent.instance().download_manager
        for download in download_manager.get_downloads():
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
                rand = random.Random()
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
        download_manager = LibtorrentComponent.instance().download_manager
        with open('downloads.txt', 'w') as downloads_file:
            downloads_file.write('infohash,status,progress\n')
            for download in download_manager.get_downloads():
                state = download.get_state()
                downloads_file.write("%s,%s,%f\n" % (
                    hexlify(download.get_def().get_infohash()),
                    dlstatus_strings[state.get_status()],
                    state.get_progress()))


class TriblerBasedModule(ExperimentModule):
    ipv8: IPv8

    def __init__(self, experiment):
        super().__init__(experiment)
        self.tribler_module.ipv8_available.add_done_callback(lambda f: self.on_ipv8_available(f.result()))
        self.strategies = {
            'RandomWalk': RandomWalk,
            'EdgeWalk': EdgeWalk,
            'RandomChurn': RandomChurn
        }

    def on_ipv8_available(self, ipv8):
        self.ipv8 = ipv8

    @property
    def tribler_module(self) -> TriblerModule:
        tribler_module = getattr(self.experiment, 'tribler_module', None)
        if tribler_module is None:
            raise RuntimeError('TriblerModule not found')
        return tribler_module

    @property
    @abstractmethod
    def community(self) -> Community:
        ...

    @experiment_callback
    def introduce_one_peer(self, peer_id):
        self.community.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

    @experiment_callback
    def introduce_peers(self, max_peers=None, excluded_peers=None):
        """
        Introduce peers to each other.
        :param max_peers: If specified, this peer will walk to this number of peers at most.
        :param excluded_peers: If specified, this method will ignore a specific peer from the introductions.
        """
        excluded_peers_list = []
        if excluded_peers:
            excluded_peers_list = [int(excluded_peer) for excluded_peer in excluded_peers.split(",")]

        if self.my_id in excluded_peers_list:
            self._logger.info("Not participating in the peer introductions!")
            return

        if not max_peers:
            # bootstrap the peer introduction, ensuring everybody knows everybody to start off with.
            for peer_id in self.all_vars.keys():
                if int(peer_id) != self.my_id and int(peer_id) not in excluded_peers_list:
                    self.community.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))
        else:
            # Walk to a number of peers
            eligible_peers = [peer_id for peer_id in self.all_vars.keys()
                              if int(peer_id) not in excluded_peers_list and int(peer_id) != self.my_id]
            rand_peer_ids = random.sample(eligible_peers, min(len(eligible_peers), int(max_peers)))
            for rand_peer_id in rand_peer_ids:
                self.community.walk_to(self.experiment.get_peer_ip_port_by_id(rand_peer_id))

    @experiment_callback
    def add_walking_strategy(self, name, max_peers, **kwargs):
        if name not in self.strategies:
            self._logger.warning("Strategy %s not found!", name)
            return

        strategy = self.strategies[name]

        self.ipv8.strategies.append((strategy(self.community, **kwargs), int(max_peers)))

    def get_peer(self, peer_id):
        target = self.all_vars[peer_id]
        address = (str(target['host']), target['port'])
        return Peer(b64decode(self.get_peer_public_key(peer_id)), address=address)

    def get_peer_public_key(self, peer_id):
        return self.all_vars[peer_id]['public_key']

    def on_id_received(self):
        # Since the IPv8 source module is loaded before any community module, the IPv8 on_id_received has
        # already completed. This means that the tribler_config is now available. So any configuration should happen in
        # overrides of this function. (Be sure to call this super though!)
        super().on_id_received()

        # We need the IPv8 peer key at this point. However, the configured session is not started yet. So we
        # generate the keys here and place them in the correct place. When the session starts it will load these keys.
        keypair = generate_keypair_trustchain()
        tribler_config = self.tribler_module.tribler_config
        save_keypair_trustchain(keypair, tribler_config.trustchain.ec_keypair_filename)
        save_pub_key_trustchain(keypair, "%s.pub" % tribler_config.trustchain.ec_keypair_filename)

        self.vars['public_key'] = b64encode(keypair.pub().key_to_bin()).decode('utf-8')
