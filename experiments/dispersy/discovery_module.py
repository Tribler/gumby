#!/usr/bin/env python2

from sys import maxint
from traceback import print_exc
from hashlib import sha1

from twisted.internet.task import LoopingCall

from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module
from gumby.modules.community_experiment_module import CommunityExperimentModule
from Tribler.dispersy.discovery.community import DiscoveryCommunity


@static_module
class DiscoveryModule(CommunityExperimentModule):

    def __init__(self, experiment):
        super(DiscoveryModule, self).__init__(experiment, DiscoveryCommunity)
        self.friends = set()
        self.preferences = set()
        self.monitor_friends_lc = None
        self._prev_scenario_statistics = {}
        self._prev_scenario_debug = {}
        self.community_launcher.community_kwargs['max_prefs'] = maxint
        self.community_launcher.community_kwargs['max_tbs'] = 25

    def on_community_loaded(self):
        self.community.my_preferences = self.get_preferences

    def get_preferences(self):
        if self.preferences:
            return list(self.preferences)

        return list(self.friends) + [self.community.my_member.mid]

    @experiment_callback
    def add_friend(self, peer_id, similarity=None):
        try:
            if peer_id != self.my_id:
                peer_id = int(peer_id)

                # if we don't get the ipport, then this peer isn't deployed to the das
                ipport = self.experiment.get_peer_ip_port_by_id(peer_id)
                key = self.experiment.get_private_keypair_by_id(peer_id)

                if ipport and key:
                    key = key.pub()
                    keyhash = self._crypto.key_to_hash(key)

                    self.friends.add(keyhash)

                    self._logger.info("friend added %s (%s) now have %d friends", peer_id, keyhash.encode('HEX'),
                                      len(self.friends))

                    if not self.monitor_friends_lc:
                        self.monitor_friends_lc = lc = LoopingCall(self.monitor_friends)
                        lc.start(5.0, now=True)
                elif ipport:
                    self._logger.error("Got ip/port, but not key? %d", peer_id)
                else:
                    self._logger.error("No ip/port or key %d", peer_id)
        except:
            print_exc()

    @experiment_callback
    def download(self, infohash):
        keyhash = sha1(str(infohash)).digest()
        self.preferences.add(keyhash)
        self._logger.info("preference added, now have %d preferences", keyhash.encode('HEX'), len(self.preferences))

    def monitor_friends(self):
        connected_friends = 0
        for mid in self.friends:
            if self.community and self.community.is_taste_buddy_mid(mid):
                connected_friends += 1

        if self.friends:
            bootstrapped = connected_friends / float(len(self.friends))
        else:
            bootstrapped = 0

        self._prev_scenario_statistics = self.print_dict_changes("scenario-statistics", self._prev_scenario_statistics, {'bootstrapped': bootstrapped})
        if self.community:
            self._prev_scenario_debug = self.print_dict_changes("scenario-debug", self._prev_scenario_debug, {'nr_friends':len(self.friends) if self.friends else 0})
