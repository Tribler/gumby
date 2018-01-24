from experiments.tunnels.tunnel_module import TunnelModule
from gumby.experiment import experiment_callback
from gumby.modules.experiment_module import static_module


@static_module
class HiddenTunnelModule(TunnelModule):

    def on_id_received(self):
        super(HiddenTunnelModule, self).on_id_received()
        self.tribler_config.set_tunnel_community_hidden_seeding(True)

    @experiment_callback
    def write_tunnels_info(self):
        super(HiddenTunnelModule, self).write_tunnels_info()

        with open('introduction_points.txt', 'w', 0) as ips_file:
            for infohash in self.community.intro_point_for.iterkeys():
                ips_file.write("%s,%s\n" % (self.my_id, infohash.encode('hex')))

        with open('rendezvous_points.txt', 'w', 0) as rps_file:
            for cookie in self.community.rendezvous_point_for.iterkeys():
                rps_file.write("%s,%s\n" % (self.my_id, cookie.encode('hex')))
