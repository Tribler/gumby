#!/usr/bin/env python3

import csv
import json
import math
import os
import sys


def is_float(x):
    """
    Check if a number can be cast to float
    """
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


def mkdir_for_file(filename):
    """
    Create a directory structure for a file
    """
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))


def large_deviation(data, point):
    """
    Check if a data point is within 1.5 IQR of the median.

    :param data: a list of previous data points
    :param point: the data point to check
    :return: whether the point is an outlier
    """
    pdf = sorted(data)
    IQR = pdf[int(math.ceil(3*len(pdf)/4))] - pdf[int(math.floor(len(pdf)/4))]
    median = pdf[int(math.floor(len(pdf)/2))]
    if int(math.floor(len(pdf)/2)) != int(math.ceil(len(pdf)/2)):
        median = (median + pdf[int(math.ceil(len(pdf)/2))])/2

    min_allowed = median - 1.5*IQR
    max_allowed = median + 1.5*IQR

    return point > max_allowed or point < min_allowed


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
        self.scenario = os.environ.get("SCENARIO_FILE", None)

    def process(self):
        """
        Process the current and historical dropped statistics.
        """
        # Stop if we have no scenario file
        if not self.scenario:
            print("Could not find scenario file")
            return 0
        # Stop if we have no data to extract
        total_dropped = self._extract_total_dropped()
        if total_dropped is None:
            print("Could not find file", self._dropped_reduced)
            return 0
        # Write the current data if we don't have old data
        if not os.path.exists(self._dropped_stats_json):
            print(self._dropped_stats_json, "does not exist, trying to create it")
            mkdir_for_file(self._dropped_stats_json)
            with open(self._dropped_stats_json, 'w') as f:
                json.dump({self.scenario: [total_dropped, ]}, f)
            return 0
        else:
            print(self._dropped_stats_json + " exists, proceeding")

        # We update the historical json with the latest statistics
        combined = self._combine_stats(self.scenario, total_dropped)
        with open(self._dropped_stats_json, 'w') as f:
            json.dump(combined, f)

        # Return if we don't have enough data, need at least 2 to compute standard deviation
        previous_values = combined[self.scenario]
        if len(previous_values) < 3:
            print("Not enough data to check deviation")
            return 0

        if large_deviation(previous_values, total_dropped):
            print("Large deviation in dropped message count detected!")
            print(total_dropped, "<<>>", sum(previous_values)/len(previous_values))
            return 1
        else:
            return 0

    def _combine_stats(self, scenario, total_dropped):
        """
        Insert the new data into the old data.

        :param scenario: the scenario name to update
        :param total_dropped: the value to update with
        :return: the new dict
        """
        stats = self._get_stats()
        values = stats.get(scenario, [])
        values.append(total_dropped)
        stats[scenario] = values[:10]
        return stats

    def _get_stats(self):
        """
        Retrieve the historical stats dict.
        """
        with open(self._dropped_stats_json) as f:
            try:
                return json.load(f)
            except ValueError:
                print(self._dropped_stats_json, "seems to be corrupt, resetting!")
                return {}

    def _extract_total_dropped(self):
        """
        Read the new count of dropped messages.
        """
        if not os.path.exists(self._dropped_reduced):
            return None

        last_row = get_last_row(self._dropped_reduced)
        if not last_row:
            return 0
        # first element is the time, not the no. of dropped messages, last element is empty string
        last_row = last_row[1:]
        last_row = [float(x) for x in last_row if is_float(x)]

        return sum(last_row)


if __name__ == '__main__':
    d = DroppedStatsProcessor()
    sys.exit(d.process())
