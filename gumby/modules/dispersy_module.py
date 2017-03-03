from os import environ, path, getpid
from collections import defaultdict
from time import time

from twisted.python.log import addObserver
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import deferLater

from gumby.sync import experiment_callback
from gumby.modules.experiment_module import static_module
from gumby.modules.base_dispersy_module import BaseDispersyModule
from gumby.modules.isolated_community_loader import IsolatedCommunityLoader
from gumby.modules.gumby_session import GumbySession

from Tribler.Core.SessionConfig import SessionStartupConfig
from Tribler.dispersy.dispersy import Dispersy
from Tribler.dispersy.crypto import ECCrypto, NoCrypto
from Tribler.dispersy.endpoint import StandaloneEndpoint
from Tribler.dispersy.util import unhandled_error_observer
from Tribler.dispersy.candidate import CANDIDATE_STUMBLE_LIFETIME, CANDIDATE_WALK_LIFETIME, CANDIDATE_INTRO_LIFETIME


@static_module
class DispersyExperimentModule(BaseDispersyModule):
    def __init__(self, experiment):
        super(DispersyExperimentModule, self).__init__(experiment)
        self._crypto = self._initialize_crypto()
        self.session_id = environ['SYNC_HOST'] + environ['SYNC_PORT']
        self.custom_community_loader = self.create_community_loader()

    def on_id_received(self):
        super(DispersyExperimentModule, self).on_id_received()
        self.session_config = self.setup_session_config()
        self.session = GumbySession(scfg=self.session_config)

    @experiment_callback
    def start_session(self):
        self._logger.debug("Starting dispersy")
        self.dispersy = Dispersy(StandaloneEndpoint(self.session_config.get_dispersy_port(), '0.0.0.0'),
                                  u'.', u"dispersy.db", self._crypto)
        self.dispersy.statistics.enable_debug_statistics(True)
        self.dispersy.start()

        self.custom_community_loader.load(self.dispersy, self.session)

        self._do_log()
        self._logger.debug("Finished starting dispersy")

    @experiment_callback
    def stop_session(self):
        self.dispersy.stop()

    @experiment_callback
    def churn(self, *args):
        self.print_on_change('community-churn', {}, {'args':args})

    def _initialize_crypto(self):
        if environ.get('TRACKER_CRYPTO', 'ECCrypto') == 'ECCrypto':
            self._logger.debug('Turning on ECCrypto')
            return ECCrypto()
        self._logger.debug('Turning off Crypto')
        return NoCrypto()

    @inlineCallbacks
    def _do_log(self):
        total_stumbled_candidates = defaultdict(lambda:defaultdict(set))

        prev_statistics = {}
        prev_total_received = {}
        prev_total_dropped = {}
        prev_total_delayed = {}
        prev_total_outgoing = {}
        prev_total_fail = {}
        prev_endpoint_recv = {}
        prev_endpoint_send = {}
        prev_created_messages = {}

        while True:
            self.dispersy.statistics.update()

            communities_dict = {}
            for c in self.dispersy.statistics.communities:

                if c._community.dispersy_enable_candidate_walker:
                    # determine current size of candidates categories
                    nr_walked = nr_intro = nr_stumbled = 0

                    # we add all candidates which have a last_stumble > now - CANDIDATE_STUMBLE_LIFETIME
                    now = time()
                    for candidate in c._community.candidates.itervalues():
                        if candidate.last_stumble > now - CANDIDATE_STUMBLE_LIFETIME:
                            nr_stumbled += 1

                            mid = candidate.get_member().mid
                            total_stumbled_candidates[c.hex_cid][candidate.last_stumble].add(mid)

                        if candidate.last_walk > now - CANDIDATE_WALK_LIFETIME:
                            nr_walked += 1

                        if candidate.last_intro > now - CANDIDATE_INTRO_LIFETIME:
                            nr_intro += 1
                else:
                    nr_walked = nr_intro = nr_stumbled = "?"

                total_nr_stumbled_candidates = sum(len(members) for members in total_stumbled_candidates[c.hex_cid].values())

                communities_dict[c.hex_cid] = {'classification': c.classification,
                                         'global_time': c.global_time,
                                         'sync_bloom_new': c.sync_bloom_new,
                                         'sync_bloom_reuse': c.sync_bloom_reuse,
                                         'sync_bloom_send': c.sync_bloom_send,
                                         'sync_bloom_skip': c.sync_bloom_skip,
                                         'nr_candidates': len(c.candidates) if c.candidates else 0,
                                         'nr_walked': nr_walked,
                                         'nr_stumbled': nr_stumbled,
                                         'nr_intro' : nr_intro,
                                         'total_stumbled_candidates': total_nr_stumbled_candidates}

            # check for missing communities, reset candidates to 0
            cur_cids = communities_dict.keys()
            for cid, c in prev_statistics.get('communities', {}).iteritems():
                if cid not in cur_cids:
                    _c = c.copy()
                    _c['nr_candidates'] = "?"
                    _c['nr_walked'] = "?"
                    _c['nr_stumbled'] = "?"
                    _c['nr_intro'] = "?"
                    communities_dict[cid] = _c

            statistics_dict = {'conn_type': self.dispersy.statistics.connection_type,
                               'received_count': self.dispersy.statistics.total_received,
                               'success_count': self.dispersy.statistics.msg_statistics.success_count,
                               'drop_count': self.dispersy.statistics.msg_statistics.drop_count,
                               'delay_count': self.dispersy.statistics.msg_statistics.delay_received_count,
                               'delay_success': self.dispersy.statistics.msg_statistics.delay_success_count,
                               'delay_timeout': self.dispersy.statistics.msg_statistics.delay_timeout_count,
                               'delay_send': self.dispersy.statistics.msg_statistics.delay_send_count,
                               'created_count': self.dispersy.statistics.msg_statistics.created_count,
                               'total_up': self.dispersy.statistics.total_up,
                               'total_down': self.dispersy.statistics.total_down,
                               'total_send': self.dispersy.statistics.total_send,
                               'cur_sendqueue': self.dispersy.statistics.cur_sendqueue,
                               'total_candidates_discovered': self.dispersy.statistics.total_candidates_discovered,
                               'walk_attempt': self.dispersy.statistics.walk_attempt_count,
                               'walk_success': self.dispersy.statistics.walk_success_count,
                               'walk_invalid_response_identifier': self.dispersy.statistics.invalid_response_identifier_count,
                               'communities': communities_dict}

            prev_statistics = self.print_on_change("statistics", prev_statistics, statistics_dict)
            prev_total_dropped = self.print_on_change("statistics-dropped-messages", prev_total_dropped, self.dispersy.statistics.msg_statistics.drop_dict)
            prev_total_delayed = self.print_on_change("statistics-delayed-messages", prev_total_delayed, self.dispersy.statistics.msg_statistics.delay_dict)
            prev_total_received = self.print_on_change("statistics-successful-messages", prev_total_received, self.dispersy.statistics.msg_statistics.success_dict)
            prev_total_outgoing = self.print_on_change("statistics-outgoing-messages", prev_total_outgoing, self.dispersy.statistics.msg_statistics.outgoing_dict)
            prev_created_messages = self.print_on_change("statistics-created-messages", prev_created_messages, self.dispersy.statistics.msg_statistics.created_dict)
            prev_total_fail = self.print_on_change("statistics-walk-fail", prev_total_fail, self.dispersy.statistics.walk_failure_dict)
            prev_endpoint_recv = self.print_on_change("statistics-endpoint-recv", prev_endpoint_recv, self.dispersy.statistics.endpoint_recv)
            prev_endpoint_send = self.print_on_change("statistics-endpoint-send", prev_endpoint_send, self.dispersy.statistics.endpoint_send)

            yield deferLater(reactor, 5.0, lambda : None)

    def setup_session_config(self):
        config = super(DispersyExperimentModule, self).setup_session_config()
        config.set_state_dir(path.abspath(path.join(environ["OUTPUT_DIR"], ".Dispersy-%d") % getpid()))
        return config
