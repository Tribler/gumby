import logging

from Tribler.pyipv8.ipv8.peer import Peer

from gumby.modules.community_launcher import IPv8CommunityLauncher
from gumby.modules.gumby_session import IPv8CommunityLoader


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

    def get_walk_strategies(self):
        return self.child.get_walk_strategies()


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
