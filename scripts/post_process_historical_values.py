#!/usr/bin/env python2

import csv
import json
import os
import numpy as np


def is_float(x):
    try:
        float(x)
        return True
    except ValueError:
        return False


def get_last_row(f, delimiter=' '):
    """
    Gets the last row of the CSV file
    :param f: The filename
    :param delimiter: The delimiter
    :return: The last row
    """
    with open(f, 'r') as f:
        last_row = None
        for last_row in csv.reader(f, delimiter=delimiter):
            pass
        return last_row


def byteify(inp):
    """
    Recursively encode an object from unicode into UTF-8, any object that is not of instance unicode is ignored.
    :param inp: The input object.
    :return: The encoded object.
    """
    if isinstance(inp, dict):
        return {byteify(key): byteify(value) for key, value in inp.iteritems()}
    elif isinstance(inp, list):
        return [byteify(element) for element in inp]
    elif isinstance(inp, unicode):
        return inp.encode('utf-8')
    else:
        return inp


def has_large_deviation(x, xs, n=1):
    """
    Checks whether x is within n standard deviations of the mean of xs.
    :param x: the latest value
    :param xs: the historical values
    :param n: number of standard deviations
    :return: True if x over n standard deviations away from the mean of the historical values, the mean and the
    standard deviation.
    """
    arr = np.array(xs)
    mean = arr.mean()
    std = arr.std()
    if abs(mean - x) > n * std:
        return True, mean, std
    return False, mean, std

def mkdir_for_file(filename):
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))

class DroppedStatsProcessor:

    def __init__(self,
                 dropped_stats_json='../historical/dropped_stats.json',
                 dropped_reduced='dropped_reduced.txt'):
        """
        Object for processing the historical average of the number of dropped messages.
        Note that the base directory is set in the parent script, usually 'output'.
        """
        self._dropped_stats_json = dropped_stats_json
        self._dropped_reduced = dropped_reduced

    def process(self, n_stats=5, n_std=3):
        """
        Process the current and historical dropped statistics.
        :param n_stats: The number of historical values to keep
        :param n_std: The latest value must be within n_std standard deviations of the historical mean for this function
        to exit successfully.
        """
        # write the current data if we don't have old data
        if not os.path.exists(self._dropped_stats_json):
            print self._dropped_stats_json + " does not exist, trying to create it"
            mkdir_for_file(self._dropped_stats_json)
            with open(self._dropped_stats_json, 'w') as f:
                json.dump([self._compute_stats()], f)
            return
        else:
            print self._dropped_stats_json + " exists, proceeding"

        # we update the historical json with the latest statistics
        combined = self._combine_stats(n_stats)
        with open(self._dropped_stats_json, 'w') as f:
            json.dump(combined, f)

        # return if we don't have enough data, need at least 2 to compute standard deviation
        if len(combined) < 3:
            return

        # TODO average can also be computed on total or maximum, which one to use?
        combined_avg = [x['average'] for x in combined]
        large_deviation, mean, std = has_large_deviation(combined_avg[0], combined_avg[1:], n_std)
        if large_deviation:
            print "large deviation detected, new_value: {}, mean: {}, n_std: {}, std: {}"\
                .format(combined_avg[0], mean, n_std, std)

    def _combine_stats(self, n):
        stats = self._get_stats()
        stats.append(self._compute_stats())
        stats.sort(key=lambda x: x['build_number'], reverse=True)
        if n > len(stats):
            n = len(stats)
        return stats[0:n]

    def _get_stats(self):
        with open(self._dropped_stats_json) as f:
            try:
                stats = json.load(f)
            except ValueError:
                stats = []
        # we expect the file to be in ASCII, so change the unicode type to UTF-8
        stats = byteify(stats)
        return stats

    def _compute_stats(self):
        if not os.path.exists(self._dropped_reduced):
            return {}

        last_row = get_last_row(self._dropped_reduced)
        # first element is the time, not the no. of dropped messages, last element is empty string
        last_row = last_row[1:-1]
        last_row = [float(x) for x in last_row if is_float(x)]
        tot = sum(last_row)
        avg = tot / float(len(last_row))

        dropped_stats_dict = {
            'build_number':  int(os.environ['BUILD_NUMBER']),
            'total': tot,
            'average': avg,
            'maximum': max(last_row)
        }

        return dropped_stats_dict


if __name__ == '__main__':
    d = DroppedStatsProcessor()
    d.process()


