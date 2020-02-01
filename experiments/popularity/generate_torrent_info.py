"""
Generate a file that contains torrent information.
This file can then be loaded in an experiment to initialize channels.
"""
import random

PEERS = 20
TORRENTS_IN_CHANNEL = 200
DEAD_TORRENT_RATE = 0.619


def random_infohash():
    """ Generates a random torrent infohash string """
    return ''.join(random.choice('0123456789abcdef') for _ in range(40))


with open("torrents.txt", "w") as torrents_file:
    for peer in range(PEERS):
        for _ in range(TORRENTS_IN_CHANNEL):
            infohash = random_infohash()
            seeders = 0 if random.random() < DEAD_TORRENT_RATE else random.randint(1, 10000)
            leechers = random.randint(0, 10000)
            torrents_file.write("%d,%s,%d,%d\n" % (peer + 1, infohash, seeders, leechers))
