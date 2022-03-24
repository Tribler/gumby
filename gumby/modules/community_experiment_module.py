from base64 import b64decode, b64encode
from random import sample
from typing import Optional

from ipv8.loader import CommunityLauncher
from ipv8.peer import Peer
from ipv8.peerdiscovery.churn import RandomChurn
from ipv8.peerdiscovery.discovery import EdgeWalk, RandomWalk

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import ExperimentModule
from gumby.util import generate_keypair_trustchain, save_keypair_trustchain, save_pub_key_trustchain


class IPv8OverlayExperimentModule(ExperimentModule):
    """
    Base class for experiment modules that provide gumby scenario control over a single IPv8 overlay.
    """

    def __init__(self, experiment, community_class):
        super(IPv8OverlayExperimentModule, self).__init__(experiment)
        self.community_class = community_class

        # To be sure that the module loading happens in the right order, this next line serves the dual purpose of
        # triggering the check for a loaded IPv8 provider
        self.ipv8_provider.ipv8_available.add_done_callback(lambda f: self.on_ipv8_available(f.result()))
        self.strategies = {
            'RandomWalk': RandomWalk,
            'EdgeWalk': EdgeWalk,
            'RandomChurn': RandomChurn
        }

    @property
    def ipv8_community_loader(self):
        return self.ipv8_provider.custom_ipv8_community_loader

    @property
    def ipv8_community_launcher(self) -> Optional[CommunityLauncher]:
        """
        Return the launcher associated with the community of this module.
        """
        for launcher, _ in self.ipv8_community_loader.community_launchers.values():
            if launcher.get_overlay_class().__name__ == self.community_class.__name__:
                return launcher
        return None

    def on_ipv8_available(self, ipv8):
        pass

    @property
    def ipv8_provider(self):
        """
        Gets an experiment module from the loaded experiment modules that inherits from BaseIPv8Module. It can be
        used as the source for the IPv8 instance, session, session config and custom community loader.
        :return: An instance of BaseIPv8Module that was loaded into the experiment.
        """
        provider = None

        for module in self.experiment.experiment_modules:
            if isinstance(module, ExperimentModule) and module.has_ipv8:
                provider = module
                break

        if provider:
            return provider

        raise Exception("No IPv8 provider module loaded. Load an implementation of BaseIPv8Module ("
                        "with has_ipv8 = True) before loading the %s module" % self.__class__.__name__)

    @property
    def ipv8(self):
        return self.ipv8_provider.ipv8

    @property
    def session(self):
        return self.ipv8_provider.session

    @property
    def tribler_config(self):
        # The tribler config only exists after on_id_received, up to session start. The session start copy constructs
        # all settings so writing to the original tribler_config after this will not do anything. So on any access to
        # the tribler_config after the session has launched, return the session. It acts as a tribler_config as well and
        # alerts the user if some setting cannot be changed at runtime.
        if self.ipv8_provider.tribler_config is None:
            return self.session

        return self.ipv8_provider.tribler_config

    @property
    def overlay(self):
        # TODO: implement MultiCommunityExperimentModule.
        # If there are multiple instances of a community class there are basically 2 approaches to solving this. One
        # is to derive from CommunityExperimentModule and override this community property, then each instance of the
        # community class can get accessed by index or some such. All @experiment_callbacks in this case would require a
        # number/name argument to indicate what community to work on. An alternative approach would be to instance a
        # CommunityExperimentModule for each instance of the community_class. However it would be difficult to separate
        # the scenario usage of its @experiment_callbacks, they would have to be dynamically named/generated.
        for overlay in self.ipv8.overlays:
            if isinstance(overlay, self.community_class):
                return overlay
        return None

    @experiment_callback
    def introduce_one_peer(self, peer_id):
        self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

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
                    self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))
        else:
            # Walk to a number of peers
            eligible_peers = [peer_id for peer_id in self.all_vars.keys()
                              if int(peer_id) not in excluded_peers_list and int(peer_id) != self.my_id]
            rand_peer_ids = sample(eligible_peers, min(len(eligible_peers), int(max_peers)))
            for rand_peer_id in rand_peer_ids:
                self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(rand_peer_id))

    @experiment_callback
    def add_walking_strategy(self, name, max_peers, **kwargs):
        if name not in self.strategies:
            self._logger.warning("Strategy %s not found!", name)
            return

        strategy = self.strategies[name]

        self.session.ipv8.strategies.append((strategy(self.overlay, **kwargs), int(max_peers)))

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
        super(IPv8OverlayExperimentModule, self).on_id_received()

        # We need the IPv8 peer key at this point. However, the configured session is not started yet. So we
        # generate the keys here and place them in the correct place. When the session starts it will load these keys.
        keypair = generate_keypair_trustchain()
        save_keypair_trustchain(keypair, self.tribler_config.trustchain.ec_keypair_filename)
        save_pub_key_trustchain(keypair, "%s.pub" % self.tribler_config.trustchain.ec_keypair_filename)

        self.vars['public_key'] = b64encode(keypair.pub().key_to_bin()).decode('utf-8')
