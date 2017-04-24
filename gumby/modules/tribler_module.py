from twisted.internet.threads import deferToThread

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module
from gumby.modules.base_dispersy_module import BaseDispersyModule


@static_module
class TriblerModule(BaseDispersyModule):
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
