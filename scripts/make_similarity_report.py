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


def getAvgMetricPerRevision():
    m = MatrixHelper(config)
    sim = m.getAvgMetricPerRevision(MetricType.COSINESIM)
    return sim


def getMatrix(revision):
    m = MatrixHelper(config)
    matrix = m.loadFromDatabase(revision, MetricType.COSINESIM)
    return matrix


def getAllRevisions():
    s = SessionHelper(config)
    revs = s.getAllRevisions(config['testname'])
    return revs


def generateRankingDocs():
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../templates'))
    loader = FileSystemLoader(searchpath=template_dir)
    env = Environment(loader=loader)
    template = env.get_template('template_ochiai_ranking.html')
    revs = getAllRevisions()
    print revs

    for rev in revs:
        matrix1 = getMatrix(rev)
        if matrix1 == None:
            continue
        # print matrix1.metrics[MetricType.COSINESIM]
        report = template.render(
                title='Ranking for revision: %s' % rev,
                matrix=matrix1
                ).encode("utf-8")
        with open(outputPath + '/ranking_%s.html' % rev, 'wb') as fh:
            fh.write(report)


def print_html_doc():
    # uses http://softwarebyjosh.com/raphy-charts/
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../templates'))

    print "Getting templates from: %s" % template_dir
    loader = FileSystemLoader(searchpath=template_dir)
    env = Environment(loader=loader)
    template = env.get_template('template_similarity_report_flot.html')
    matrix1 = getMatrix("7c90df94327eb12d25cc063a191728e5fecb21d6")
    print matrix1.metrics[MetricType.COSINESIM]
    report = template.render(
            title='Similarity report',
            similarity=getAvgMetricPerRevision(),
            # matrix=matrix1
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
    # print outputPath
    # getSimilarityPerStacktrace()
    generateRankingDocs()

    print_html_doc()

