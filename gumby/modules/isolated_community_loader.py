import logging

from Tribler.pyipv8.ipv8.peer import Peer

from gumby.modules.community_launcher import DispersyCommunityLauncher, IPv8CommunityLauncher
from gumby.modules.gumby_session import DispersyCommunityLoader, IPv8CommunityLoader


class IsolatedDispersyLauncherWrapper(DispersyCommunityLauncher):

    """
    Wrapper for another CommunityLauncher:
    Changes the master member.
    """

    def __init__(self, child, session_id):
        """
        Wrap a child launcher, given a unique session id.

        :type child: DispersyCommunityLauncher
        :type session_id: str
        """
        self.child = child
        self.session_id = session_id

    @property
    def community_args(self):
        return self.child.community_args

    @property
    def community_kwargs(self):
        return self.child.community_kwargs

    def get_name(self):
        return self.child.get_name()

    def not_before(self):
        return self.child.not_before()

    def should_launch(self, session):
        return self.child.should_launch(session)

    def prepare(self, dispersy, session):
        self.child.prepare(dispersy, session)

    def finalize(self, dispersy, session, _):
        """
        Perform our own init_community() with our custom master member.
        """
        from gumby.modules.ipv8_module import IPV8
        if isinstance(dispersy, IPV8):

            if hasattr(self.get_community_class(), "master_peer"):
                # Old style/deprecated IPv8 community
                community = self.get_community_class()(self.get_my_member(dispersy, session),
                                                       endpoint=self.dispersy.endpoint, network=self.dispersy.network,
                                                       *self.get_args(session), **self.get_kwargs(session))
                community.master_peer = self.get_master_member(dispersy)
            else:
                # New style IPv8 community
                community = self.get_community_class()(self.get_master_member(dispersy),
                                                       self.get_my_member(dispersy, session),
                                                       endpoint=self.dispersy.endpoint, network=self.dispersy.network,
                                                       *self.get_args(session), **self.get_kwargs(session))
        else:
            # Dispersy community
            community = self.get_community_class().init_community(dispersy,
                                                                  self.get_master_member(dispersy),
                                                                  self.get_my_member(dispersy, session),
                                                                  *self.get_args(session),
                                                                  **self.get_kwargs(session))
        self.child.finalize(dispersy, session, community)

    def get_community_class(self):
        return self.child.get_community_class()

    def get_my_member(self, dispersy, session):
        return self.child.get_my_member(dispersy, session)

    def get_master_member(self, dispersy):
        """
        Generate a master member with our registered unique id for our wrapped community.

        :type dispersy: Tribler.dispersy.dispersy.Dispersy
        :rtype: Tribler.dispersy.member.Member
        """
        from Tribler.dispersy.crypto import ECCrypto
        eccrypto = ECCrypto()
        unique_id = self.get_name() + self.session_id
        private_bin = "".join([unique_id[i] if i < len(unique_id) else "0" for i in range(68)])
        eckey = eccrypto.key_from_private_bin("LibNaCLSK:" + private_bin)
        master_key = eckey.pub().key_to_bin()
        return dispersy.get_member(public_key=master_key)

    def should_load_now(self, session):
        """
        Do not let Dispersy load the community, we will do this ourselves in finalize().
        """
        return False

    def get_args(self, session):
        return self.child.get_args(session)

    def get_kwargs(self, session):
        return self.child.get_kwargs(session)


class IsolatedIPv8LauncherWrapper(IPv8CommunityLauncher):

    """
    Wrapper for another CommunityLauncher:
    Changes the master member.
    """

    def __init__(self, child, session_id):
        """
        Wrap a child launcher, given a unique session id.

        :type child: IPv8CommunityLauncher
        :type session_id: str
        """
        self.child = child
        self.session_id = session_id

    @property
    def community_args(self):
        return self.child.community_args

    @property
    def community_kwargs(self):
        return self.child.community_kwargs

    def get_name(self):
        return self.child.get_name()

    def not_before(self):
        return self.child.not_before()

    def should_launch(self, session):
        return self.child.should_launch(session)

    def prepare(self, ipv8, session):
        self.child.prepare(ipv8, session)

    def finalize(self, ipv8, session, overlay):
        """
        We change the master peer of the created overlay.
        """
        from Tribler.pyipv8.ipv8.keyvault.crypto import ECCrypto
        eccrypto = ECCrypto()
        unique_id = self.get_name() + self.session_id
        private_bin = "".join([unique_id[i] if i < len(unique_id) else "0" for i in range(68)])
        eckey = eccrypto.key_from_private_bin("LibNaCLSK:" + private_bin)
        master_peer = Peer(eckey.pub().key_to_bin())
        overlay.master_peer = master_peer

        self.child.finalize(ipv8, session, overlay)

    def get_overlay_class(self):
        return self.child.get_overlay_class()

    def get_my_peer(self, ipv8, session):
        return self.child.get_my_peer(ipv8, session)

    def get_args(self, session):
        return self.child.get_args(session)

    def get_kwargs(self, session):
        return self.child.get_kwargs(session)


class IsolatedDispersyCommunityLoader(DispersyCommunityLoader):

    """
    Extension of DispersyCommunityLoader, allowing for isolation of registered Dispersy community launchers.

    In other words, this allows the configuration of communities with
    a different master member.
    """

    def __init__(self, session_id):
        """
        Create a new isolated community loader.

        IsolatedCommunityLoaders on different machines using the same session_id
        and the same community will share the same master member.
        In all other cases they will not share the same master member.

        :type session_id: str
        """
        assert isinstance(session_id, str)

        super(IsolatedDispersyCommunityLoader, self).__init__()

        self.session_id = session_id
        self.isolated = []

    def isolate(self, name):
        """
        Isolate a community by name.

        See CommunityLauncher.get_name()
        :type name: str
        """
        assert name in self.community_launchers.keys()

        if name in self.isolated:
            logging.warning("re-isolation of %s: you probably did not want to do this", name)
        else:
            self.isolated.append(name)

        self.set_launcher(IsolatedDispersyLauncherWrapper(self.get_launcher(name), self.session_id))


class IsolatedIPv8CommunityLoader(IPv8CommunityLoader):

    """
    Extension of IPv8CommunityLoader, allowing for isolation of registered IPv8 overlay launchers.

    In other words, this allows the configuration of communities with a different master peer.
    """

    def __init__(self, session_id):
        """
        Create a new isolated community loader.

        IsolatedCommunityLoaders on different machines using the same session_id
        and the same community will share the same master member.
        In all other cases they will not share the same master member.

        :type session_id: str
        """
        assert isinstance(session_id, str)

        super(IsolatedIPv8CommunityLoader, self).__init__()

        self.session_id = session_id
        self.isolated = []

    def isolate(self, name):
        """
        Isolate a community by name.

        See CommunityLauncher.get_name()
        :type name: str
        """
        assert name in self.community_launchers.keys()

        if name in self.isolated:
            logging.warning("re-isolation of %s: you probably did not want to do this", name)
        else:
            self.isolated.append(name)

        self.set_launcher(IsolatedIPv8LauncherWrapper(self.get_launcher(name), self.session_id))
