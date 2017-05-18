from os import path
from collections import defaultdict
from time import time

from twisted.internet.task import LoopingCall

from gumby.experiment import experiment_callback
from gumby.modules.community_launcher import DiscoveryCommunityLauncher
from gumby.modules.experiment_module import static_module
from gumby.modules.base_dispersy_module import BaseDispersyModule

from Tribler.dispersy.dispersy import Dispersy
from Tribler.dispersy.crypto import ECCrypto, NoCrypto, M2CryptoSK
from Tribler.dispersy.endpoint import StandaloneEndpoint
from Tribler.dispersy.candidate import CANDIDATE_STUMBLE_LIFETIME, CANDIDATE_WALK_LIFETIME, CANDIDATE_INTRO_LIFETIME

from Tribler.Core import permid


@static_module
class DispersyModule(BaseDispersyModule):
    def __init__(self, experiment):
        super(DispersyModule, self).__init__(experiment)
        self.crypto = ECCrypto()
        self._do_log_lc = LoopingCall(self._do_log)
        self.custom_community_loader.set_launcher(DiscoveryCommunityLauncher())

    @experiment_callback
    def start_session(self):
        super(DispersyModule, self).start_session()

        self._logger.info("Starting dispersy")
        self.dispersy = Dispersy(StandaloneEndpoint(self.session.config.get_dispersy_port(), '0.0.0.0'),
                                 unicode(self.session.config.get_state_dir()), u"dispersy.db", self.crypto)
        self.dispersy.statistics.enable_debug_statistics(True)
        self.dispersy.start(autoload_discovery=False)

        pairfilename = self.session.config.get_permid_keypair_filename()
        if not path.exists(pairfilename):
            keypair = permid.generate_keypair()
            permid.save_keypair(keypair, pairfilename)
            permid.save_pub_key(keypair, "%s.pub" % pairfilename)

        private_key = self.crypto.key_to_bin(M2CryptoSK(filename=pairfilename))
        self.session.dispersy_member = self.dispersy.get_member(private_key=private_key)

        self.custom_community_loader.load(self.dispersy, self.session)
        self.session.config.set_anon_proxy_settings(2, ("127.0.0.1",
                                                        self.session.config.get_tunnel_community_socks5_listen_ports()))

        self._do_log_lc.start(5.0, True)
        self._logger.info("Finished starting dispersy")
        self.dispersy_available.callback(self.dispersy)

    @experiment_callback
    def stop_session(self):
        self.dispersy.stop()

    @experiment_callback
    def churn(self, *args):
        self.print_dict_changes('community-churn', {}, {'args':args})

    @experiment_callback
    def set_dispersy_crypto(self, value):
        if value == 'NoCrypto':
            self.crypto = NoCrypto()
        elif value != "ECCrypto":
            self._logger.warning('set_disperys_crypto argument invalid, defaulting to ECCrypto')
            self.crypto = ECCrypto()

    def _do_log(self):
        if not hasattr(self, "_do_log_env") or not self._do_log_env:
            self._do_log_env = {
                "total_stumbled_candidates": defaultdict(lambda: defaultdict(set)),
                "prev_statistics": {},
                "prev_total_received": {},
                "prev_total_dropped": {},
                "prev_total_delayed": {},
                "prev_total_outgoing": {},
                "prev_total_fail": {},
                "prev_endpoint_recv": {},
                "prev_endpoint_send": {},
                "prev_created_messages": {}
            }

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
                        self._do_log_env["total_stumbled_candidates"][c.hex_cid][candidate.last_stumble].add(mid)

                    if candidate.last_walk > now - CANDIDATE_WALK_LIFETIME:
                        nr_walked += 1

                    if candidate.last_intro > now - CANDIDATE_INTRO_LIFETIME:
                        nr_intro += 1
            else:
                nr_walked = nr_intro = nr_stumbled = "?"

            total_nr_stumbled_candidates = sum(len(members) for members in self._do_log_env["total_stumbled_candidates"][c.hex_cid].values())

            communities_dict[c.hex_cid] = {
                'classification': c.classification,
                'global_time': c.global_time,
                'sync_bloom_new': c.sync_bloom_new,
                'sync_bloom_reuse': c.sync_bloom_reuse,
                'sync_bloom_send': c.sync_bloom_send,
                'sync_bloom_skip': c.sync_bloom_skip,
                'nr_candidates': len(c.candidates) if c.candidates else 0,
                'nr_walked': nr_walked,
                'nr_stumbled': nr_stumbled,
                'nr_intro' : nr_intro,
                'total_stumbled_candidates': total_nr_stumbled_candidates
            }

        # check for missing communities, reset candidates to 0
        cur_cids = communities_dict.keys()
        for cid, c in self._do_log_env["prev_statistics"].get('communities', {}).iteritems():
            if cid not in cur_cids:
                _c = c.copy()
                _c['nr_candidates'] = "?"
                _c['nr_walked'] = "?"
                _c['nr_stumbled'] = "?"
                _c['nr_intro'] = "?"
                communities_dict[cid] = _c

        self._do_log_env["statistics_dict"] = {
            'conn_type': self.dispersy.statistics.connection_type,
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
            'communities': communities_dict
        }

        self._do_log_env["prev_statistics"] = self.print_dict_changes("statistics", self._do_log_env["prev_statistics"], self._do_log_env["statistics_dict"])
        self._do_log_env["prev_total_dropped"] = self.print_dict_changes("statistics-dropped-messages", self._do_log_env["prev_total_dropped"], self.dispersy.statistics.msg_statistics.drop_dict)
        self._do_log_env["prev_total_delayed"] = self.print_dict_changes("statistics-delayed-messages", self._do_log_env["prev_total_delayed"], self.dispersy.statistics.msg_statistics.delay_dict)
        self._do_log_env["prev_total_received"] = self.print_dict_changes("statistics-successful-messages", self._do_log_env["prev_total_received"], self.dispersy.statistics.msg_statistics.success_dict)
        self._do_log_env["prev_total_outgoing"] = self.print_dict_changes("statistics-outgoing-messages", self._do_log_env["prev_total_outgoing"], self.dispersy.statistics.msg_statistics.outgoing_dict)
        self._do_log_env["prev_created_messages"] = self.print_dict_changes("statistics-created-messages", self._do_log_env["prev_created_messages"], self.dispersy.statistics.msg_statistics.created_dict)
        self._do_log_env["prev_total_fail"] = self.print_dict_changes("statistics-walk-fail", self._do_log_env["prev_total_fail"], self.dispersy.statistics.walk_failure_dict)
        self._do_log_env["prev_endpoint_recv"] = self.print_dict_changes("statistics-endpoint-recv", self._do_log_env["prev_endpoint_recv"], self.dispersy.statistics.endpoint_recv)
        self._do_log_env["prev_endpoint_send"] = self.print_dict_changes("statistics-endpoint-send", self._do_log_env["prev_endpoint_send"], self.dispersy.statistics.endpoint_send)
