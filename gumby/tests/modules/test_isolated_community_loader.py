import unittest

from gumby.modules.community_launcher import CommunityLauncher
from gumby.modules.isolated_community_loader import IsolatedLauncherWrapper


class MockDispersy(object):

    def get_member(self, public_key):
        return public_key


class MockUniqueLauncher1(CommunityLauncher):

    def get_name(self):
        return "MockUniqueLauncher1"

    def get_community_class(self):
        pass


class MockUniqueLauncher2(CommunityLauncher):

    def get_name(self):
        return "MockUniqueLauncher2"

    def get_community_class(self):
        pass


class TestIsolatedLauncherWrapper(unittest.TestCase):

    def setUp(self):
        self.session_id = "".join([chr(i) for i in range(64)])
        self.dispersy = MockDispersy()

    def test_same_id_same_name(self):
        """
        A master member is shared if session_ids and community names match
        """
        wrapper1 = IsolatedLauncherWrapper(MockUniqueLauncher1(), self.session_id)
        wrapper2 = IsolatedLauncherWrapper(MockUniqueLauncher1(), self.session_id)

        self.assertEqual(wrapper1.get_master_member(self.dispersy),
                         wrapper2.get_master_member(self.dispersy))

    def test_unique_id_same_name(self):
        """
        A master member is unique if session_ids differ and community names match
        """
        wrapper1 = IsolatedLauncherWrapper(MockUniqueLauncher1(), self.session_id)
        wrapper2 = IsolatedLauncherWrapper(MockUniqueLauncher1(), "I am something else")

        self.assertNotEqual(wrapper1.get_master_member(self.dispersy),
                            wrapper2.get_master_member(self.dispersy))

    def test_same_id_unique_name(self):
        """
        A master member is unique if session_ids match and community names are unique
        """
        wrapper1 = IsolatedLauncherWrapper(MockUniqueLauncher1(), self.session_id)
        wrapper2 = IsolatedLauncherWrapper(MockUniqueLauncher2(), self.session_id)

        self.assertNotEqual(wrapper1.get_master_member(self.dispersy),
                            wrapper2.get_master_member(self.dispersy))

    def test_unique_id_unique_name(self):
        """
        A master member is unique if session_ids and community names are unique
        """
        wrapper1 = IsolatedLauncherWrapper(MockUniqueLauncher1(), self.session_id)
        wrapper2 = IsolatedLauncherWrapper(MockUniqueLauncher2(), "I am something else")

        self.assertNotEqual(wrapper1.get_master_member(self.dispersy),
                            wrapper2.get_master_member(self.dispersy))
