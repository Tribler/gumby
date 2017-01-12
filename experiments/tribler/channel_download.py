#!/usr/bin/env python2
import logging
import os
from binascii import hexlify, unhexlify
from os import path as path
from sys import path as pythonpath
import time

import posix

from twisted.internet import reactor
from twisted.internet.task import LoopingCall

from gumby.experiments.TriblerDispersyClient import TriblerDispersyExperimentScriptClient, BASE_DIR
from gumby.experiments.dispersyclient import main, DispersyExperimentScriptClient

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))
pythonpath.append('.')

from Tribler.Core.DownloadConfig import DefaultDownloadStartupConfig
from Tribler.Core.TorrentDef import TorrentDef
from Tribler.community.channel.community import ChannelCommunity
from Tribler.community.channel.preview import PreviewChannelCommunity
from Tribler.Policies.credit_mining_util import TorrentManagerCM
from Tribler.Core.RemoteTorrentHandler import RemoteTorrentHandler

class ChannelDownloadClient(TriblerDispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        super(ChannelDownloadClient, self).__init__(*argv, **kwargs)
        from Tribler.community.allchannel.community import AllChannelCommunity
        self.community_class = AllChannelCommunity

        self._logger.setLevel(logging.DEBUG)

        self.my_channel = None
        self.joined_community = None

        self.join_lc = None
        self.dl_lc = {}

        self.upload_dir_path = None

        self.torrent_mgr = None
        self.downloaded_torrent = {}

        self.num_peers = -1

        self.id_experiment = os.environ['EXPERIMENT_NAME'].replace(" ", "")

    def start_session(self):
        super(ChannelDownloadClient, self).start_session()
        self.session_deferred.addCallback(self.__config_dispersy)
        self.session_deferred.addErrback(self._logger.error)

        self.num_peers = os.environ.get('das4_instances_to_run', -1)
        if self.num_peers == -1:
            self._logger.error("Cannot get var:das4_instances_to_run")
            self.num_peers = os.environ.get('sync_subscribers_amount', -1)
            if self.num_peers == -1:
                self._logger.error("Cannot get var:sync_subscribers_amount")
                self.num_peers = len(self.get_peers()) or 200

    def __config_dispersy(self, session):

        count_out = 0
        while self._dispersy is None and count_out < 100:
            time.sleep(1.0)
            count_out += 1

        self.session.lm.dispersy = self._dispersy
        # self.session.lm.init()
        self.session.get_dispersy = True

        self._dispersy.define_auto_load(ChannelCommunity, self._my_member, (), {"tribler_session": self.session})
        self._dispersy.define_auto_load(PreviewChannelCommunity, self._my_member, (), {"tribler_session": self.session})

        from Tribler.Core.TFTP.handler import TftpHandler

        self.session.lm.tftp_handler = TftpHandler(self.session, self.endpoint,
                                                   "fffffffd".decode('hex'), block_size=1024)
        self.session.lm.tftp_handler.initialize()

        self.session.lm.rtorrent_handler = RemoteTorrentHandler(self.session)
        self.session.get_dispersy_instance = lambda: self.session.lm.dispersy
        self.session.lm.rtorrent_handler.initialize()

        self._logger.error("Dispersy configured")

    def start_dispersy(self):
        DispersyExperimentScriptClient.start_dispersy(self)

    def setup_session_config(self):
        config = super(ChannelDownloadClient, self).setup_session_config()
        config.set_state_dir(os.path.abspath(os.path.join(posix.environ.get('OUTPUT_DIR', None) or BASE_DIR, "Tribler-%d") % os.getpid()))
        config.set_megacache(True)
        config.set_dht_torrent_collecting(True)
        config.set_torrent_collecting(False)
        config.set_torrent_store(True)
        config.set_enable_multichain(False)
        config.set_tunnel_community_enabled(False)
        config.set_channel_community_enabled(False)
        config.set_preview_channel_community_enabled(False)

        config.set_dispersy(False)

        self.upload_dir_path = path.join(config.get_state_dir(), "..", "upload_dir")
        if not os.path.exists(self.upload_dir_path):
            try:
                os.makedirs(self.upload_dir_path)
            except OSError:
                # race condition of creating shared directory may happen
                # this particular issue can be found in DAS environment which we can't control where to put a node
                # usually, the publisher handles the directory creation, in DAS case, this is not entirely the case
                pass

        logging.debug("Do session config locally")
        return config

    def online(self, dont_empty=False):
        self.set_community_kwarg("tribler_session", self.session)
        self.set_community_kwarg("auto_join_channel", True)

        super(ChannelDownloadClient, self).online()

        settings = self.session.lm.ltmgr.get_session().get_settings()
        settings['allow_multiple_connections_per_ip'] = True
        settings['ignore_limits_on_local_network'] = False
        self.session.lm.ltmgr.get_session().set_settings(settings)
        self.set_speed(250000, 100000)

        self.torrent_mgr = TorrentManagerCM(self.session)

    def registerCallbacks(self):
        super(ChannelDownloadClient, self).registerCallbacks()

        self.scenario_runner.register(self.create, 'create')
        self.scenario_runner.register(self.join, 'join')
        self.scenario_runner.register(self.publish, 'publish')
        self.scenario_runner.register(self.start_download, 'start_download')
        self.scenario_runner.register(self.stop_download, 'stop_download')
        self.scenario_runner.register(self.setup_seeder, 'setup_seeder')
        self.scenario_runner.register(self.set_speed, 'set_speed')

    def create(self):
        self._logger.error("creating-community")
        self.my_channel = ChannelCommunity.create_community(self._dispersy, self._my_member, tribler_session=self.session)
        self.my_channel.set_channel_mode(ChannelCommunity.CHANNEL_OPEN)
        self.my_channel._disp_create_channel(u'channel-name', u'channel-desc')

        self._logger.error("Community %s (%s) created with member: %s",
                           self.my_channel.get_channel_name(), self.my_channel.get_channel_id(), self.my_channel._master_member)

    def set_speed(self, download, upload):
        settings = self.session.lm.ltmgr.get_session().get_settings()
        settings['download_rate_limit'] = int(download)
        settings["upload_rate_limit"] = int(upload)
        self.session.lm.ltmgr.get_session().set_settings(settings)

    def join(self):
        if not self.join_lc:
            self.join_lc = lc = LoopingCall(self.join)
            lc.start(1.0, now=False)

        self._logger.error("trying-to-join-community on %s", self._community)

        if self._community is None:
            return

        channels = self._community._channelcast_db.getAllChannels()

        if channels:
            cid = channels[0][1]
            community = self._community._get_channel_community(cid)
            if community._channel_id:

                self._community.disp_create_votecast(community.cid, 2, int(time.time()))

                self._logger.error("joining-community")
                for c in self._dispersy.get_communities():
                    if isinstance(c, ChannelCommunity):
                        self.joined_community = c
                if self.joined_community is None:
                    self._logger.error("couldn't join community")
                self._logger.error("Joined community with member: %s", self.joined_community._master_member)
                self.join_lc.stop()
                return

    def __ds_active_callback(self, ds):
        from Tribler.Core.simpledefs import dlstatus_strings

        thandle = ds.get_download().handle
        availability = 0.0
        if thandle:
            num_peers = thandle.status().num_peers
            num_pieces, _ = ds.get_pieces_total_complete()

            if num_peers * num_pieces:
                for p_num in thandle.piece_availability():
                    tmp = float(p_num) / float(num_peers * num_pieces)
                    availability += tmp

        peers = [x for x in ds.get_peerlist() if any(x['have']) and not
                 x['ip'].startswith("127.0.0")]

        ds.get_peerlist = lambda: peers

        setting = self.session.lm.ltmgr.get_session().get_settings()
        dlmax = setting['download_rate_limit']
        ulmax = setting['upload_rate_limit']

        self._logger.error('%s:%s infohash=%s, downsp=%d, upsp=%d, progress=%s, status=%s, peers=%s rat=%s dl=%s up=%s avail=%.8f dsavail=%.8f' %
                          (self._dispersy.lan_address[0], self._dispersy.lan_address[1],
                           ds.get_download().tdef.get_infohash().encode('hex')[:5],
                           min(ds.get_current_speed('down'), dlmax + 100000)/1000,
                           min(ds.get_current_speed('up'), ulmax + 100000)/1000,
                           ds.get_progress(),
                           dlstatus_strings[ds.get_status()],
                           len(peers),
                           ds.seeding_ratio,
                           ds.get_total_transferred('down')/1000,
                           ds.get_total_transferred('up')/1000,
                           availability,
                           ds.get_availability()))

        if ds.get_progress() == 0.0 and ds.get_status() == 3:
            self._connect_peer(ds.get_download().handle)

        return 1.0, True

    def setup_seeder(self, filename, size):
        exp_filename = self.id_experiment + "_" + filename
        tpath = path.join(self.upload_dir_path, "%s.data" % exp_filename)
        tdef = None
        if path.isfile(tpath):
            tpath = path.join(self.upload_dir_path, "%s.torrent" % exp_filename)

            if path.isfile(tpath):
                tdef = TorrentDef.load(tpath)
            else:
                # writing file has not finished yet
                reactor.callLater(10.0, self.setup_seeder, filename, size)
        else:
            # file not found. In DAS case, this is because the file is in another node
            tdef = self._create_test_torrent(exp_filename, size)

        if tdef:
            dscfg = DefaultDownloadStartupConfig.getInstance().copy()
            dscfg.set_dest_dir(self.upload_dir_path)
            dscfg.set_hops(0)
            dscfg.set_safe_seeding(False)
            dscfg.dlconfig.set('downloadconfig', 'seeding_mode', 'forever')

            self._logger.error("Setup seeder for %s", hexlify(tdef.get_infohash()))

            download = self.session.start_download_from_tdef(tdef, dscfg)
            download.set_state_callback(self.__ds_active_callback, True)

    def publish(self, filename, size):
        if self.my_channel or self.joined_community:
            tdef = self._create_test_torrent(self.id_experiment + "_" + filename, size)
            if self.my_channel:
                self.my_channel._disp_create_torrent_from_torrentdef(tdef, int(time.time()))
            elif self.joined_community:
                self.joined_community._disp_create_torrent_from_torrentdef(tdef, int(time.time()))

            self.setup_seeder(filename, size)
        else:
            self._logger.debug("Can't publish yet, no channel or community joined")
            reactor.callLater(10.0, self.publish, filename, size)

    def _create_test_torrent(self, filename='', size=0):
        filepath = path.join(self.upload_dir_path, "%s.data" % filename)

        tdef = TorrentDef()
        with open(filepath, 'wb') as fp:
            fp.write("0" * int(size))

        tdef.add_content(filepath)

        # doesn't matter for now
        tdef.set_tracker("http://127.0.0.1:9197/announce")
        tdef.finalize()

        tdef_file = path.join(self.upload_dir_path, "%s.torrent" % filename)
        tdef.save(tdef_file)

        self._logger.error("Created %s torrent (%s) with size %s", filename, hexlify(tdef.get_infohash()), size)

        return tdef

    def _connect_peer(self, thandle):
        for cd in self.joined_community.dispersy_yield_verified_candidates():
            ip = cd.lan_address[0]
            for port in xrange(20000, 20000 + self.num_peers + 10):
                if thandle:
                    thandle.connect_peer((ip, port), 0)

    def start_download(self, name):
        name = name if name.startswith(self.id_experiment) else self.id_experiment + "_" + name
        if name not in self.dl_lc.keys():
            self.dl_lc[name] = LoopingCall(self.start_download, name)
            self.dl_lc[name].start(1.0, now=False)

            self.downloaded_torrent[name] = False
        elif self.downloaded_torrent[name]:
            self.dl_lc[name].stop()
            self.dl_lc[name] = None

            tdef = TorrentDef.load_from_memory(self.session.get_collected_torrent(
                                               unhexlify(self.downloaded_torrent[name])))

            self._logger.error("%s.torrent %s (%s) found, prepare to download..",
                               name, self.downloaded_torrent[name], tdef)

            dscfg = DefaultDownloadStartupConfig.getInstance().copy()
            dscfg.set_dest_dir(path.join(self.session.get_state_dir(), "download"))
            dscfg.set_hops(0)
            dscfg.set_safe_seeding(False)
            dscfg.dlconfig.set('downloadconfig', 'seeding_mode', 'forever')

            self._logger.error("Start downloading for %s", hexlify(tdef.get_infohash()))

            download_impl = self.session.start_download_from_tdef(tdef, dscfg)
            download_impl.set_state_callback(self.__ds_active_callback, True)

            self._connect_peer(download_impl.handle)

        if not self.joined_community:
            self._logger.error("Pending download")
            return

        #shameless copy from boostingsource
        CHANTOR_DB = ['ChannelTorrents.channel_id', 'Torrent.torrent_id', 'infohash', 'Torrent.name', 'length',
                          'category', 'status', 'num_seeders', 'num_leechers', 'ChannelTorrents.id',
                          'ChannelTorrents.dispersy_id', 'ChannelTorrents.name', 'Torrent.name',
                          'ChannelTorrents.description', 'ChannelTorrents.time_stamp', 'ChannelTorrents.inserted']
        infohash_bin = None
        torrent_values = self.joined_community._channelcast_db.getTorrentsFromChannelId(self.joined_community.get_channel_id(), True, CHANTOR_DB)
        if torrent_values:
            log = "Channel id %s : " % self.joined_community.get_channel_id()
            for t in torrent_values:
                torrent_name = t[3]
                log += "%s(%s) " % (t[3], hexlify(t[2]))

                if torrent_name[:-5] == name:
                    infohash_bin = t[2]

            self._logger.error(log)

            if infohash_bin:

                self._logger.error("Find %s with ihash %s", name, hexlify(infohash_bin))
                for candidate in list(self.joined_community.dispersy_yield_candidates()):

                    def _success_download(ihash_str):
                        self.downloaded_torrent[name] = ihash_str

                    self.session.lm.rtorrent_handler.download_torrent(
                        candidate, infohash_bin, user_callback=_success_download, priority=1)

                    self.session.lm.rtorrent_handler.download_torrent(
                        None, infohash_bin, user_callback=_success_download, priority=1)

        self._logger.error("Pending download")

    def stop_download(self, dname):
        dname = self.id_experiment + "_" + dname
        for name in self.dl_lc.keys():
            if name == dname:
                lc = self.dl_lc.pop(name)
                if not self.downloaded_torrent[name]:
                    self._logger.error("Can't make it to download %s", name)
                    lc.stop()
                else:
                    ihash = unhexlify(self.downloaded_torrent[dname])
                    d_impl = self.session.get_download(ihash)
                    self._logger.error("Stopping Download %s", self.downloaded_torrent[dname])
                    self.session.remove_download_by_id(ihash, True, True)

    def stop(self, retry=3):

        # stop stalled download
        for name in self.dl_lc.keys():
            if not self.downloaded_torrent[name]:
                self.dl_lc.pop(name).stop()
                self._logger.error("Can't make it to download %s", name)

        downloads_impl = self.session.get_downloads()
        if downloads_impl:
            for d in downloads_impl:
                self._logger.error("Clean download %s", hexlify(d.tdef.get_infohash()))
                self.session.remove_download(d, True, True)

            reactor.callLater(10.0, self.stop, retry)
        else:
            super(ChannelDownloadClient, self).stop()

if __name__ == '__main__':
    ChannelDownloadClient.scenario_file = os.environ.get('SCENARIO_FILE', 'channel_download.scenario')
    main(ChannelDownloadClient)
