from binascii import unhexlify

from ipv8.community import Community
from ipv8.lazy_community import lazy_wrapper
from ipv8.loader import overlay
from ipv8.messaging.lazy_payload import VariablePayload, vp_compile
from ipv8.types import Peer

from gumby.experiment import experiment_callback
from gumby.modules.community_experiment_module import IPv8OverlayExperimentModule
from gumby.modules.experiment_module import static_module
from gumby.modules.ipv8_community_launchers import IPv8CommunityLauncher


# ---- messages ---- #
@vp_compile
class PingPayload(VariablePayload):
    msg_id = 1


@vp_compile
class PongPayload(VariablePayload):
    msg_id = 2


# ---- community ---- #
class PingPongCommunity(Community):
    community_id = unhexlify("d37c847b628e1414cffb6a4626b7fa0999fba888")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_message_handler(PingPayload, self.received_ping)
        self.add_message_handler(PongPayload, self.received_pong)

    def send_ping(self):
        for peer in self.network.verified_peers:
            self.logger.info("Sending ping to peer %s", peer)
            self.ez_send(peer, PingPayload())

    @lazy_wrapper(PingPayload)
    def received_ping(self, peer: Peer, _: PingPayload):
        self.logger.info("Received ping from peer %s", peer)
        self.ez_send(peer, PongPayload())

    @lazy_wrapper(PongPayload)
    def received_pong(self, peer: Peer, _: PongPayload):
        self.logger.info("Received pong from peer %s", peer)


# ---- launcher ---- #
@overlay(PingPongCommunity)
class PingPongCommunityLauncher(IPv8CommunityLauncher):
    pass


# ---- module ---- #
@static_module
class PingPongModule(IPv8OverlayExperimentModule):
    """
    This module contains code to manage experiments with the Basalt community.
    """
    def __init__(self, experiment):
        super().__init__(experiment, PingPongCommunity)

    def on_id_received(self):
        super().on_id_received()
        self.ipv8_provider.custom_ipv8_community_loader.set_launcher(PingPongCommunityLauncher())

    @experiment_callback
    def send_ping(self):
        self.overlay.send_ping()
