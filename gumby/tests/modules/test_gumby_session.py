import unittest

from gumby.modules.community_launcher import CommunityLauncher
from gumby.modules.gumby_session import CommunityLoader


class MockCommunity(object):
    pass


class MockDispersy(object):

    def __init__(self):
        self.loaded_classes = []

    def define_auto_load(self, community_class, *args):
        self.loaded_classes.append(community_class.__name__)


class MockUniqueLauncher(CommunityLauncher):

    def get_name(self):
        return str(id(self))

    def get_community_class(self):
        return MockCommunity

    def get_my_member(self, dispersy, session):
        return None


class TestCommunityLoader(unittest.TestCase):

    def setUp(self):
        self.loader = CommunityLoader()
        self.dispersy = MockDispersy()

    def test_unknown_dependency(self):
        """
        If a dependency does not exist, the community should be loaded.

        This avoids waiting forever for something which does not exist.
        """
        launcher = MockUniqueLauncher()
        launcher.not_before = lambda: "I don't exist"
        self.loader.set_launcher(launcher)
        self.loader.load(self.dispersy, None)

        self.assertListEqual(self.dispersy.loaded_classes, ["MockCommunity",])

    def test_cycle_dependency(self):
        """
        In case of programmer cyclic dependency error, raise a RuntimeError
        """
        launcher1 = MockUniqueLauncher()
        launcher2 = MockUniqueLauncher()
        launcher3 = MockUniqueLauncher()
        launcher1.not_before = lambda: [launcher2.get_name(),]
        launcher2.not_before = lambda: [launcher3.get_name(),]
        launcher3.not_before = lambda: [launcher1.get_name(),]
        self.loader.set_launcher(launcher1)
        self.loader.set_launcher(launcher2)
        self.loader.set_launcher(launcher3)

        self.assertRaises(RuntimeError, self.loader.load, self.dispersy, None)
