#!/usr/bin/env python2
from experiments.dispersy.extract_dispersy_statistics import AbstractHandler, get_parser
import os
import sys
import logging


class TunnelStatistics(AbstractHandler):

    def __init__(self):
        AbstractHandler.__init__(self)

    def filter_line(self, node_nr, line_nr, timestamp, timeoffset, key):
        return key in ["speed-download", "speed-upload", "progress-percentage"]

    def new_file(self, node_nr, filename, outputdir):
        self.h_downloadstats = open(os.path.join(outputdir, "speed_download.txt"), 'w+')
        self.h_uploadstats = open(os.path.join(outputdir, "speed_upload.txt"), 'w+')
        self.h_progress = open(os.path.join(outputdir, "progress_percentage.txt"), 'w+')
        print >> self.h_downloadstats, "#", "timestamp", "timeoffset", "download"
        print >> self.h_uploadstats, "#", "timestamp", "timeoffset", "upload"
        print >> self.h_progress, "#", "timestamp", "timeoffset", "progress"

    def handle_line(self, node_nr, line_nr, timestamp, timeoffset, key, json):
        if key == 'speed-download':
            print >> self.h_downloadstats, timestamp, timeoffset, json['download']
        elif key == 'speed-upload':
            print >> self.h_uploadstats, timestamp, timeoffset, json['upload']
        elif key == 'progress-percentage':
            print >> self.h_progress, timestamp, timeoffset, json['progress']

    def all_files_done(self, extract_statistics):
        self.h_downloadstats.close()
        self.h_uploadstats.close()
        self.h_progress.close()
        extract_statistics.merge_records("speed_download.txt", 'speed_download_reduced.txt', 2, 'speed_download_diff.txt')
        extract_statistics.merge_records("speed_upload.txt", 'speed_upload_reduced.txt', 2, 'speed_upload_diff.txt')
        extract_statistics.merge_records("progress_percentage.txt", 'progress_percentage_reduced.txt', 2, 'progress_percentage_diff.txt')

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Usage: %s <node-directory> <messagestoplot>" % (sys.argv[0])
        print >> sys.stderr, sys.argv

        sys.exit(1)

    e = get_parser(sys.argv)
    e.add_handler(TunnelStatistics())
    e.parse()
