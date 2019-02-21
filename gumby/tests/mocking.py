class MockOverlay(object):

    def __init__(self, *args, **kwargs):
        pass


class MockConfig(object):

    def get_ipv8_statistics(self):
        return False


class MockSession(object):

    def __init__(self):
        self.config = MockConfig()


class MockIPv8(object):

    def __init__(self):
        self.endpoint = None
        self.network = None
        self.overlays = []
