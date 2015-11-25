class MultiChainSyntheticExperiment:
    """
    Experiment runner that can synthesize an upload of an particular speed.
    """
    def __init__(self):
        self.time = 200

    def start_download(self, seed, leecher, size, speed):
        """
        Start an synthetic download.
        :param seed: The seeder
        :param leecher: The leecher
        :param size: The total size in KB of the download.
        :param speed: The speed of the download
        """
        ticks = size / speed
        time = self.time
        for i in range(0, ticks):
            """ Download every 1 s."""
            time += 1
            self._write(time, seed, leecher, speed)
        """ Download remainder. """
        time += 1
        self._write(time, seed, leecher, size % speed)

    def _write(self, time, seed, leecher, speed):
        print "@0:%s increase_kbytes_received %s %s {%s}" % tuple(map(str, (time, seed, speed, leecher)))
        print "@0:%s increase_kbytes_sent %s %s {%s}" % tuple(map(str, (time, leecher, speed, seed)))


MultiChainSyntheticExperiment().start_download(1, 2, 10000000, 1000)
#print ""
#MultiChainSyntheticExperiment().start_download(2, 3, 100000, 1000)
print ""
#MultiChainSyntheticExperiment().start_download(3, 4, 100000, 1000)
print ""
