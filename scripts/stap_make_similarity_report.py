#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
import os
from jinja2 import Environment, FileSystemLoader
from gumby.settings import loadConfig
# from spectraperf.databasehelper import *
from gumby.spectraperf.performanceprofile import MatrixHelper, MetricType, SessionHelper
# THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def getSimilarityPerStacktrace():
    m = MatrixHelper(config)
    sim = m.getMetricPerStacktrace(MetricType.COSINESIM)
    return sim


def getAvgMetricPerRevision():
    m = MatrixHelper(config)
    sim = m.getAvgMetricPerRevision(MetricType.COSINESIM)
    return sim


def getTotalBytesWrittenPerRevision():
    m = MatrixHelper(config)
    tb = m.getTotalBytesWrittenPerRevision()
    return tb


def getMatrix(revision):
    m = MatrixHelper(config)
    matrix = m.loadFromDatabase(revision, MetricType.COSINESIM)
    return matrix


def getAllRevisions():
    s = SessionHelper(config)
    revs = s.getAllRevisions(config['testname'])
    return revs


def getCallsPerStacktrace(rev):
    m = MatrixHelper(config)
    calls = m.getCallsPerStacktrace(rev)
    return calls


def generateRankingDocs():
    global tool
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib/templates'))
    loader = FileSystemLoader(searchpath=template_dir)
    env = Environment(loader=loader)
    template = env.get_template('template_ochiai_ranking.html')
    revs = getAllRevisions()

    for rev in revs:
        matrix1 = getMatrix(rev)
        callsPerStacktrace = getCallsPerStacktrace(rev)
        if matrix1 == None:
            continue
        # print matrix1.metrics[MetricType.COSINESIM]
        report = template.render(
                title='Ranking for revision: %s' % rev,
                matrix=matrix1,
                callsPerStacktrace=callsPerStacktrace,
                tool=tool
                ).encode("utf-8")
        with open(outputPath + '/ranking_%s.html' % rev, 'wb') as fh:
            fh.write(report)


def generateSimReport():
    global tool
    global testcase
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib/templates'))

    print "Getting templates from: %s" % template_dir
    loader = FileSystemLoader(searchpath=template_dir)
    env = Environment(loader=loader)
    template = env.get_template('template_similarity_report_flot.html')
    report = template.render(
            title='Similarity report',
            # similarity=getAvgMetricPerRevision(),
            similarity=getTotalBytesWrittenPerRevision(),
            # matrix=matrix1
            tool=tool,
            testcase=testcase
            ).encode("utf-8")
    with open(outputPath + '/sim_report.html', 'wb') as fh:
        fh.write(report)

    # generate summary report for display on the job main page
    template = env.get_template('template_similarity_report_summary.html')
    report = template.render(
            title='Similarity report summary',
            similarity=getTotalBytesWrittenPerRevision(),
            tool=tool,
            testcase=testcase
            ).encode("utf-8")
    with open(outputPath + '/sim_report_summary.html', 'wb') as fh:
        fh.write(report)

if __name__ == '__main__':
    if len(sys.argv) == 5:
        config = loadConfig(sys.argv[1])
        outputPath = os.path.abspath(sys.argv[2])
        tool = sys.argv[3]
        testcase = sys.argv[4]
    else:
        print 'usage python make_similarity_report.py confFile outputPath toolname testcase'
        exit()
    # print outputPath
    # getSimilarityPerStacktrace()
    generateRankingDocs()
    generateSimReport()
