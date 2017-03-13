import logging

from gumby.modules.community_launcher import CommunityLauncher
from gumby.modules.gumby_session import DefaultCommunityLoader

from Tribler.dispersy.crypto import ECCrypto


class IsolatedLauncherWrapper(CommunityLauncher):

    """
    Wrapper for another CommunityLauncher:
    Changes the master member.
    """

    def __init__(self, child, session_id):
        """
        Wrap a child launcher, given a unique session id.

        :type child: CommunityLauncher
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


class IsolatedCommunityLoader(DefaultCommunityLoader):

    """
    Extension of DefaultCommunityLoader, allowing for isolation
    of registered community launchers.

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

        super(IsolatedCommunityLoader, self).__init__()

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

        self.set_launcher(IsolatedLauncherWrapper(self.get_launcher(name), self.session_id))
