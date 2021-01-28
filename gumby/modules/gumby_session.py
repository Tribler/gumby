import os
import time as timemod
from socket import gethostbyname

from ipv8.bootstrapping.dispersy.bootstrapper import DispersyBootstrapper
from ipv8.loader import IPv8CommunityLoader

from tribler_core.session import Session


class GumbySession(Session):
    """
    Overwritten Session allowing for custom community loading.
    """

    def __init__(self, config=None, ipv8_community_loader=IPv8CommunityLoader()):
        super(GumbySession, self).__init__(config)
        self.ipv8_community_loader = ipv8_community_loader

    def inject_bootstrappers(self):
        """
        We manually update the IPv8 bootstrap servers since IPv8 does not use the bootstraptribler.txt file.
        """
        head_host = gethostbyname(os.environ['HEAD_HOST']) if 'HEAD_HOST' in os.environ else "127.0.0.1"
        dns_addresses = []

        my_state_path = self.config.get_state_dir()
        bootstrap_file = os.path.join(os.environ['OUTPUT_DIR'], 'bootstraptribler.txt')
        if os.path.exists(bootstrap_file):
            os.symlink(bootstrap_file, os.path.join(my_state_path, 'bootstraptribler.txt'))

            with open(bootstrap_file, 'r') as bfile:
                for line in bfile.readlines():
                    parts = line.split(" ")
                    if not parts:
                        continue
                    dns_addresses.append((parts[0], int(parts[1])))

        base_tracker_port = int(os.environ['TRACKER_PORT'])
        port_range = range(base_tracker_port, base_tracker_port + 4)
        with open(os.path.join(my_state_path, 'bootstraptribler.txt'), "w+") as f:
            f.write("\n".join(["%s %d" % (head_host, port) for port in port_range]))
        ip_addresses = [(head_host, port) for port in port_range]

        for overlay in self.ipv8.overlays:
            overlay.bootstrappers = [DispersyBootstrapper(ip_addresses, dns_addresses)]

    def load_ipv8_overlays(self):
        self._logger.info("tribler: Preparing IPv8 overlays...")
        now_time = timemod.time()

        self.ipv8_community_loader.load(self.ipv8, self)

        self.inject_bootstrappers()

        if self.config.get_ipv8_statistics():
            for overlay in self.ipv8.overlays:
                self.ipv8.endpoint.enable_community_statistics(overlay.get_prefix(), True)

        self.config.set_anon_proxy_settings(2,
                                            ("127.0.0.1",
                                             self.config.get_tunnel_community_socks5_listen_ports()))

        self._logger.info("tribler: IPv8 overlays are ready in %.2f seconds", timemod.time() - now_time)
