from gumby.sync import experiment_callback
from gumby.experiments.experiment_module import ExperimentModule, static_module


@static_module
class DispersyExperimentModule(ExperimentModule):
    def __init__(self, experiment):
        super(DispersyExperimentModule, self).__init__()
        self._logger.info("I got attached to experiment %s" % repr(experiment))

        self._dispersy = None
        self._community = None
        self._database_file = u"dispersy.db"
        self._dispersy_exit_status = None
        self._is_joined = False
        self._strict = True
        self.community_args = []
        self.community_kwargs = {}

        self._crypto = self._initialize_crypto()
        self._generate_my_member()
        experiment.vars['private_keypair'] = base64.encodestring(self.my_member_private_key)

        # self.scenario_runner.register(self.online)
        # self.scenario_runner.register(self.offline)
        # self.scenario_runner.register(self.churn)
        # self.scenario_runner.register(self.churn, 'churn_pattern')
        # self.scenario_runner.register(self.set_community_kwarg)
        # self.scenario_runner.register(self.set_database_file)
        # self.scenario_runner.register(self.use_memory_database)
        # self.scenario_runner.register(self.set_ignore_exceptions)
        # self.scenario_runner.register(self.start_dispersy)
        # self.scenario_runner.register(self.stop_dispersy)
        # self.scenario_runner.register(self.stop)
        # self.scenario_runner.register(self.set_master_member)
        # self.scenario_runner.register(self.reset_dispersy_statistics, 'reset_dispersy_statistics')

    @property
    def my_member_key_curve(self):
        # low (NID_sect233k1) isn't actually that low, switching to 160bits as this is comparable to rsa 1024
        # http://www.nsa.gov/business/programs/elliptic_curve.shtml
        # speed difference when signing/verifying 100 items
        # NID_sect233k1 signing took 0.171 verify took 0.35 totals 0.521
        # NID_secp160k1 signing took 0.04 verify took 0.04 totals 0.08
        return u"NID_secp160k1"

    @experiment_callback
    def set_community_args(self, *args):
        """
        Example: '1292333014 12923340000'
        """
        self.community_args = args

    @experiment_callback
    def set_community_kwargs(self, **kwargs):
        """
        Example: 'startingtimestamp=1292333014 endingtimestamp=12923340000'
        """
        self.community_kwargs = kwargs

    @experiment_callback
    def set_community_kwarg(self, key, value):
        self.community_kwargs[key] = value

    @experiment_callback
    def set_database_file(self, filename):
        self._database_file = unicode(filename)

    @experiment_callback
    def use_memory_database(self):
        self._database_file = u':memory:'

    @experiment_callback
    def set_ignore_exceptions(self, boolean):
        self._strict = not self.str2bool(boolean)

    @experiment_callback
    def start_dispersy(self, autoload_discovery=True):
        self._logger.debug("Starting dispersy")
        # We need to import the stuff _AFTER_ configuring the logging stuff.
        try:
            from Tribler.dispersy.dispersy import Dispersy
            from Tribler.dispersy.endpoint import StandaloneEndpoint
            from Tribler.dispersy.util import unhandled_error_observer
        except:
            from dispersy.dispersy import Dispersy
            from dispersy.endpoint import StandaloneEndpoint
            from dispersy.util import unhandled_error_observer

        self._dispersy = Dispersy(StandaloneEndpoint(int(self.my_id) + 12000, '0.0.0.0'), u'.', self._database_file, self._crypto)
        self._dispersy.statistics.enable_debug_statistics(True)

        if self._strict:
            from twisted.python.log import addObserver
            addObserver(unhandled_error_observer)

        self._dispersy.start(autoload_discovery=autoload_discovery)

        self._master_member = self._get_master_member()
        self._my_member = self._get_my_member()

        self._do_log()

        self.print_on_change('community-kwargs', {}, self.community_kwargs)
        self.print_on_change('community-env', {}, {'pid':getpid()})

        self._logger.debug("Finished starting dispersy")

    @experiment_callback
    def stop_dispersy(self):
        self._dispersy_exit_status = self._dispersy.stop()

    @experiment_callback
    def stop(self, retry=3):
        retry = int(retry)
        if self._dispersy_exit_status is None and retry:
            reactor.callLater(1, self.stop, retry - 1)
        else:
            self._logger.debug("Dispersy exit status was: %s", self._dispersy_exit_status)
            reactor.callLater(0, reactor.stop)

    @experiment_callback
    def set_master_member(self, pub_key, priv_key=''):
        self.master_key = pub_key.decode("HEX")
        self.master_private_key = priv_key.decode("HEX")

    @experiment_callback
    def online(self):
        self._logger.debug("Trying to go online")
        if self._community is None:
            self._logger.debug("online")

            self._logger.debug("join community %s as %s",
                               self._master_member.mid.encode("HEX"),
                               self._my_member.mid.encode("HEX"))

            self._community = self.community_class.init_community(self._dispersy, self._master_member, self._my_member,
                                                                  *self.community_args, **self.community_kwargs)
            self._community.auto_load = False
            assert self.is_online()
            self._logger.debug("Dispersy is using port %s", repr(self._dispersy._endpoint.get_address()))
        else:
            self._logger.debug("online (we are already online)")

    @experiment_callback
    def offline(self):
        self._logger.debug("Trying to go offline")

        if self._community is None and self._is_joined:
            self._logger.debug("offline (we are already offline)")
        else:
            self._logger.debug("offline")
            for community in self._dispersy.get_communities():
                community.unload_community()
            self._community = None

        if self._database_file == u':memory:':
            self._logger.debug("Be careful with memory databases and nodes going offline, "
                               "you could be losing database because we're closing databases.")

    @experiment_callback
    def reset_dispersy_statistics(self):
        self._dispersy._statistics.reset()

    @experiment_callback
    def churn(self, *args):
        self.print_on_change('community-churn', {}, {'args':args})

    def is_online(self):
        return self._community != None

    def _get_my_member(self):
        return self._dispersy.get_member(private_key=self.my_member_private_key)

    def _generate_my_member(self):
        ec = self._crypto.generate_key(self.my_member_key_curve)
        self.my_member_key = self._crypto.key_to_bin(ec.pub())
        self.my_member_private_key = self._crypto.key_to_bin(ec)

    def _initialize_crypto(self):
        try:
            from Tribler.dispersy.crypto import ECCrypto, NoCrypto
        except:
            from dispersy.crypto import ECCrypto, NoCrypto

        if environ.get('TRACKER_CRYPTO', 'ECCrypto') == 'ECCrypto':
            self._logger.debug('Turning on ECCrypto')
            return ECCrypto()
        self._logger.debug('Turning off Crypto')
        return NoCrypto()

    @inlineCallbacks
    def _do_log(self):
        try:
            from Tribler.dispersy.candidate import CANDIDATE_STUMBLE_LIFETIME, CANDIDATE_WALK_LIFETIME, CANDIDATE_INTRO_LIFETIME
        except:
            from dispersy.candidate import CANDIDATE_STUMBLE_LIFETIME, CANDIDATE_WALK_LIFETIME, CANDIDATE_INTRO_LIFETIME
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
            self._dispersy.statistics.update()

            communities_dict = {}
            for c in self._dispersy.statistics.communities:

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

            statistics_dict = {'conn_type': self._dispersy.statistics.connection_type,
                               'received_count': self._dispersy.statistics.total_received,
                               'success_count': self._dispersy.statistics.msg_statistics.success_count,
                               'drop_count': self._dispersy.statistics.msg_statistics.drop_count,
                               'delay_count': self._dispersy.statistics.msg_statistics.delay_received_count,
                               'delay_success': self._dispersy.statistics.msg_statistics.delay_success_count,
                               'delay_timeout': self._dispersy.statistics.msg_statistics.delay_timeout_count,
                               'delay_send': self._dispersy.statistics.msg_statistics.delay_send_count,
                               'created_count': self._dispersy.statistics.msg_statistics.created_count,
                               'total_up': self._dispersy.statistics.total_up,
                               'total_down': self._dispersy.statistics.total_down,
                               'total_send': self._dispersy.statistics.total_send,
                               'cur_sendqueue': self._dispersy.statistics.cur_sendqueue,
                               'total_candidates_discovered': self._dispersy.statistics.total_candidates_discovered,
                               'walk_attempt': self._dispersy.statistics.walk_attempt_count,
                               'walk_success': self._dispersy.statistics.walk_success_count,
                               'walk_invalid_response_identifier': self._dispersy.statistics.invalid_response_identifier_count,
                               'is_online': self.is_online(),
                               'communities': communities_dict}

            prev_statistics = self.print_on_change("statistics", prev_statistics, statistics_dict)
            prev_total_dropped = self.print_on_change("statistics-dropped-messages", prev_total_dropped, self._dispersy.statistics.msg_statistics.drop_dict)
            prev_total_delayed = self.print_on_change("statistics-delayed-messages", prev_total_delayed, self._dispersy.statistics.msg_statistics.delay_dict)
            prev_total_received = self.print_on_change("statistics-successful-messages", prev_total_received, self._dispersy.statistics.msg_statistics.success_dict)
            prev_total_outgoing = self.print_on_change("statistics-outgoing-messages", prev_total_outgoing, self._dispersy.statistics.msg_statistics.outgoing_dict)
            prev_created_messages = self.print_on_change("statistics-created-messages", prev_created_messages, self._dispersy.statistics.msg_statistics.created_dict)
            prev_total_fail = self.print_on_change("statistics-walk-fail", prev_total_fail, self._dispersy.statistics.walk_failure_dict)
            prev_endpoint_recv = self.print_on_change("statistics-endpoint-recv", prev_endpoint_recv, self._dispersy.statistics.endpoint_recv)
            prev_endpoint_send = self.print_on_change("statistics-endpoint-send", prev_endpoint_send, self._dispersy.statistics.endpoint_send)

            yield deferLater(reactor, 5.0, lambda : None)

