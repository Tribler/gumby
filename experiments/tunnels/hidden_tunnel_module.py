from experiments.tunnels.tunnel_module import TunnelModule
from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module

from tribler_core.utilities.unicode import hexlify


@static_module
class HiddenTunnelModule(TunnelModule):

    @experiment_callback
    def write_tunnels_info(self):
        super(HiddenTunnelModule, self).write_tunnels_info()

        with open('introduction_points.txt', 'w') as ips_file:
            for infohash in self.overlay.intro_point_for.keys():
                ips_file.write("%s,%s\n" % (self.my_id, hexlify(infohash)))

        with open('rendezvous_points.txt', 'w') as rps_file:
            for cookie in self.overlay.rendezvous_point_for.keys():
                rps_file.write("%s,%s\n" % (self.my_id, hexlify(cookie)))
