#!/usr/bin/env python
from os import path, environ
from sys import path as pythonpath

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, main

from twisted.python.log import msg

pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))


from doubleentry_client import DoubleEntryClient
from Tribler.community.doubleentry.community import DoubleEntryCommunity


class DoubleEntryTimeoutClient(DoubleEntryClient):

    def __init__(self, *args, **kwargs):
        super(DoubleEntryTimeoutClient, self).__init__(DoubleEntryCommunity, *args, **kwargs)




if __name__ == '__main__':
    DoubleEntryClient.scenario_file = environ.get('SCENARIO_FILE', 'doubleentry.scenario')
    main(DoubleEntryClient)