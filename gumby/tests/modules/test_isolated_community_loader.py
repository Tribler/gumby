import unittest

from gumby.modules.community_launcher import IPv8CommunityLauncher
from gumby.modules.isolated_community_loader import IsolatedIPv8LauncherWrapper
from gumby.tests.mocking import MockIPv8, MockSession, MockOverlay


class MockUniqueLauncher1(IPv8CommunityLauncher):

    def get_name(self):
        return "MockUniqueLauncher1"

    def get_overlay_class(self):
        return MockOverlay

    def get_my_peer(self, ipv8, session):
        return None


class MockUniqueLauncher2(IPv8CommunityLauncher):

    def get_name(self):
        return "MockUniqueLauncher2"

    def get_overlay_class(self):
        return MockOverlay

    def get_my_peer(self, ipv8, session):
        return None


class TestIsolatedLauncherWrapper(unittest.TestCase):

    def setUp(self):
        self.session_id = "".join([chr(i) for i in range(64)])
        self.ipv8 = MockIPv8()

    def test_same_id_same_name(self):
        """
        A master member is shared if session_ids and community names match
        """
        overlay1 = MockOverlay()
        overlay2 = MockOverlay()

        wrapper1 = IsolatedIPv8LauncherWrapper(MockUniqueLauncher1(), self.session_id)
        wrapper1.finalize(self.ipv8, MockSession(), overlay1)
        wrapper2 = IsolatedIPv8LauncherWrapper(MockUniqueLauncher1(), self.session_id)
        wrapper2.finalize(self.ipv8, MockSession(), overlay2)

        self.assertEqual(overlay1.master_peer, overlay2.master_peer)

    def test_unique_id_same_name(self):
        """
        A master member is unique if session_ids differ and community names match
        """
        overlay1 = MockOverlay()
        overlay2 = MockOverlay()

        wrapper1 = IsolatedIPv8LauncherWrapper(MockUniqueLauncher1(), self.session_id)
        wrapper1.finalize(self.ipv8, MockSession(), overlay1)
        wrapper2 = IsolatedIPv8LauncherWrapper(MockUniqueLauncher1(), "definitely something else")
        wrapper2.finalize(self.ipv8, MockSession(), overlay2)

        self.assertNotEqual(overlay1.master_peer, overlay2.master_peer)

    def test_same_id_unique_name(self):
        """
        A master member is unique if session_ids match and community names are unique
        """
        overlay1 = MockOverlay()
        overlay2 = MockOverlay()

        wrapper1 = IsolatedIPv8LauncherWrapper(MockUniqueLauncher1(), self.session_id)
        wrapper1.finalize(self.ipv8, MockSession(), overlay1)
        wrapper2 = IsolatedIPv8LauncherWrapper(MockUniqueLauncher2(), self.session_id)
        wrapper2.finalize(self.ipv8, MockSession(), overlay2)

        self.assertNotEqual(overlay1.master_peer, overlay2.master_peer)

    def test_unique_id_unique_name(self):
        """
        A master member is unique if session_ids and community names are unique
        """
        overlay1 = MockOverlay()
        overlay2 = MockOverlay()

        wrapper1 = IsolatedIPv8LauncherWrapper(MockUniqueLauncher1(), self.session_id)
        wrapper1.finalize(self.ipv8, MockSession(), overlay1)
        wrapper2 = IsolatedIPv8LauncherWrapper(MockUniqueLauncher2(), "definitely something else")
        wrapper2.finalize(self.ipv8, MockSession(), overlay2)

        self.assertNotEqual(overlay1.master_peer, overlay2.master_peer)
