from os import path, remove
from posix import environ

import keyring
from keyrings.alt.file import PlaintextKeyring
from twisted.internet import reactor
from twisted.internet.threads import deferToThread

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module
from gumby.modules.base_dispersy_module import BaseDispersyModule

from Tribler.Core.DownloadConfig import DefaultDownloadStartupConfig
from Tribler.Core.simpledefs import dlstatus_strings
from Tribler.Core.TorrentDef import TorrentDef


@static_module
class TriblerModule(BaseDispersyModule):

    def __init__(self, experiment):
        super(TriblerModule, self).__init__(experiment)
        self.transfer_size = 25 * 1024 * 1024
        self.dispersy = None
        self.ipv8 = None
        self.download_stats = {
            'download': 0,
            'progress': 0.0,
            'upload': 0
        }

        # We don't use the system keychain but a PlainText keyring for performance during tests
        self._logger.info("Available keyrings: %s", keyring.backend.get_all_keyring())
        for new_keyring in keyring.backend.get_all_keyring():
            if isinstance(new_keyring, PlaintextKeyring):
                self._logger.info("Setting keyring: %s", new_keyring)
                keyring.set_keyring(new_keyring)

    @experiment_callback
    def start_session(self):
        super(TriblerModule, self).start_session()

        self._logger.error("Starting Tribler Session")

        if self.custom_dispersy_community_loader:
            self.session.lm.dispersy_community_loader = self.custom_dispersy_community_loader

        if self.custom_ipv8_community_loader:
            self.session.lm.ipv8_community_loader = self.custom_ipv8_community_loader

        def on_tribler_started(_):
            self._logger.error("Tribler Session started")
            self.dispersy = self.session.lm.dispersy
            self.ipv8 = self.session.lm.ipv8
            self.dispersy_available.callback(self.dispersy)

        return self.session.start().addCallback(on_tribler_started)

    @experiment_callback
    def stop_session(self):
        deferToThread(self.session.shutdown)

    @experiment_callback
    def set_transfer_size(self, size):
        self.transfer_size = long(size)

    @experiment_callback
    def set_libtorrentmgr_alert_mask(self, mask=0xffffffff):
        self.session.lm.ltmgr.default_alert_mask = mask
        self.session.lm.ltmgr.alert_callback = self._process_libtorrent_alert
        for ltsession in self.session.lm.ltmgr.ltsessions.itervalues():
            ltsession.set_alert_mask(mask)

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
    def transfer(self, action="download", file_name=None, hops=None, timeout=None):
        assert action in ("download", "seed"), "Invalid transfer kind"

        if file_name is None:
            file_name = path.basename(environ["SCENARIO_FILE"])
        else:
            file_name = path.basename(environ["SCENARIO_FILE"]) + '-' + file_name

        file_name += str(self.experiment.server_vars["global_random"])

        if hops is not None:
            hops = int(hops)
            self._logger.info('Start transfer: %s file "%s" with %d hop(s)', action, file_name, hops)
        else:
            self._logger.info('Start transfer: %s file "%s"', action, file_name)

        tdef = self.create_test_torrent(file_name)
        dscfg = DefaultDownloadStartupConfig.getInstance().copy()
        if hops is not None:
            dscfg.set_hops(hops)
        dscfg.set_dest_dir(path.join(environ["OUTPUT_DIR"], str(self.my_id)))
        if action == "download":
            remove(path.join(dscfg.get_dest_dir(), file_name))

        def cb(ds):
            self._logger.info('transfer: %s infohash=%s, hops=%d, down=%d, up=%d, progress=%s, status=%s, seeds=%s',
                              action,
                              tdef.get_infohash().encode('hex')[:5],
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

        self.session.start_download_from_tdef(tdef, dscfg).set_state_callback(cb)

        if timeout:
            reactor.callLater(long(timeout), self.session.remove_download_by_id, tdef.infohash, remove_content=True,
                              remove_state=True)

    @experiment_callback
    def add_peer_to_downloads(self, peer_nr):
        self._logger.info("Adding peer %s to all downloads", peer_nr)
        host, port = self.experiment.get_peer_ip_port_by_id(peer_nr)
        for download in self.session.get_downloads():
            download.add_peer((host, port))

    def create_test_torrent(self, file_name):
        if not path.exists(file_name):
            self._logger.info("Creating torrent data file %s", file_name)
            with open(file_name, 'wb') as fp:
                fp.write("0" * self.transfer_size)

        tdef = TorrentDef()
        tdef.add_content(file_name)
        tdef.set_tracker("http://fake.net/announce")
        tdef.finalize()
        return tdef

    def _process_libtorrent_alert(self, alert):
        self._logger.info("LibtorrentDownloadImpl: alert %s", alert)

    @experiment_callback
    def write_overlay_statistics(self):
        """
        Write information about the IPv8 overlay networks to a file.
        """
        with open('overlays.txt', 'w', 0) as overlays_file:
            overlays_file.write("name,pub_key\n")
            for overlay in self.session.lm.ipv8.overlays:
                overlays_file.write("%s,%s\n" % (overlay.__class__.__name__,
                                                 overlay.my_peer.public_key.key_to_bin().encode('hex')))
