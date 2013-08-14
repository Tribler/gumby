#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from jinja2 import Environment, FileSystemLoader
from spectraperf.databasehelper import *
from spectraperf.performanceprofile import *
# THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def getSimilarityPerStacktrace():
    m = MatrixHelper(config)
    sim = m.getMetricPerStacktrace(MetricType.COSINESIM)
    return sim


def print_html_doc():
    # uses http://softwarebyjosh.com/raphy-charts/
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../templates'))

    print "Getting templates from: %s" % template_dir
    loader = FileSystemLoader(searchpath=template_dir)
    env = Environment(loader=loader)
    template = env.get_template('template_similarity_report.html')
    sim = getSimilarityPerStacktrace()
    print sim
    report = template.render(
            title='Similarity report',
            similarity=sim
            ).encode("utf-8")
    with open(outputPath + '/sim_report.html', 'wb') as fh:
        fh.write(report)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        config = loadConfig(sys.argv[1])
        outputPath = os.path.abspath(sys.argv[2])
    else:
        print 'usage python make_similarity_report.py confFile outputPath'
        exit()
    print outputPath
    # getSimilarityPerStacktrace()
    print_html_doc()
