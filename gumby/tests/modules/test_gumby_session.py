import unittest

from gumby.modules.community_launcher import IPv8CommunityLauncher
from gumby.modules.community_loader import IPv8CommunityLoader
from gumby.tests.mocking import MockOverlay, MockIPv8, MockSession


class MockUniqueLauncher(IPv8CommunityLauncher):

    def get_name(self):
        return str(id(self))

    def get_overlay_class(self):
        return MockOverlay

    def get_my_peer(self, ipv8, session):
        return None


class TestCommunityLoader(unittest.TestCase):

    def setUp(self):
        self.loader = IPv8CommunityLoader()
        self.ipv8 = MockIPv8()

    def test_unknown_dependency(self):
        """
        If a dependency does not exist, the community should be loaded.

        This avoids waiting forever for something which does not exist.
        """
        launcher = MockUniqueLauncher()
        launcher.not_before = lambda: "I don't exist"
        self.loader.community_launchers = {}
        self.loader.set_launcher(launcher)
        self.loader.load(self.ipv8, MockSession())

        self.assertTrue(self.ipv8.overlays)

    def test_cycle_dependency(self):
        """
        In case of programmer cyclic dependency error, raise a RuntimeError
        """
        launcher1 = MockUniqueLauncher()
        launcher2 = MockUniqueLauncher()
        launcher3 = MockUniqueLauncher()
        launcher1.not_before = lambda: [launcher2.get_name(), ]
        launcher2.not_before = lambda: [launcher3.get_name(), ]
        launcher3.not_before = lambda: [launcher1.get_name(), ]
        self.loader.community_launchers = {}
        self.loader.set_launcher(launcher1)
        self.loader.set_launcher(launcher2)
        self.loader.set_launcher(launcher3)

        self.assertRaises(RuntimeError, self.loader.load, self.ipv8, None)
