from os import path, remove
from posix import environ
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
        self.download_stats = {
            'download': 0,
            'progress': 0.0,
            'upload': 0
        }

    @experiment_callback
    def start_session(self):
        super(TriblerModule, self).start_session()

        self._logger.error("Starting Tribler Session")

        if self.custom_community_loader:
            self.session.lm.community_loader = self.custom_community_loader

        def on_tribler_started(_):
            self._logger.error("Tribler Session started")
            self.dispersy = self.session.lm.dispersy
            self.dispersy_available.callback(self.dispersy)

        return self.session.start().addCallback(on_tribler_started)

    @experiment_callback
    def stop_session(self):
        deferToThread(self.session.shutdown)

    @experiment_callback
    def set_transfer_size(self, size):
        self.transfer_size = long(size)

    @experiment_callback
    def transfer(self, action="download", file_name=None, hops=None):
        assert action in ("download", "seed"), "Invalid transfer kind"

        if file_name is None:
            file_name = path.basename(environ["SCENARIO_FILE"])
        else:
            file_name = path.basename(environ["SCENARIO_FILE"]) + '-' + file_name

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
            self._logger.info('transfer: %s infohash=%s, hops=%d, down=%s, up=%d, progress=%s, status=%s, seeds=%s',
                              action,
                               tdef.get_infohash().encode('hex')[:5],
                              hops,
                              ds.get_current_speed('down'),
                              ds.get_current_speed('up'),
                              ds.get_progress(),
                              dlstatus_strings[ds.get_status()],
                              sum(ds.get_num_seeds_peers()))

            new_download_stats = {
                'download': ds.get_current_speed('down'),
                'progress': ds.get_progress() * 100,
                'upload': ds.get_current_speed('up')
            }
            self.download_stats = self.print_dict_changes("download-stats", self.download_stats, new_download_stats)

            return 1.0, False

        self.session.start_download_from_tdef(tdef, dscfg).set_state_callback(cb)

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

