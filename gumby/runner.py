#!/usr/bin/env python
# run.py ---
#
# Filename: run.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Wed Jun  5 14:47:19 2013 (+0200)

# Commentary:
#
#
#
#

# Change Log:
#
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
#
#

# Code:

import sys
from os import path, chdir
from os.path import basename
from exceptions import RuntimeError

from twisted.python.log import err, msg, Logger
from twisted.internet.defer import Deferred, DeferredList, inlineCallbacks, setDebugging, gatherResults

from twisted.internet.protocol import ProcessProtocol
from twisted.internet import reactor

from sshclient import runRemoteCMD

setDebugging(True)

class ExperimentRunner(Logger):
    def __init__(self, config):
        self._config = config
        self._remote_workspace_dir = "Experiment_" + basename(config['workspace_dir'])
        # TODO: check if the experiment dir actually exists
        self._experiment_dir = path.abspath(config['workspace_dir'])

    def logPrefix(self):
        return "ExperimentRunner"

    def copyWorkspaceToHeadNodes(self):
        def onCopySuccess(ignored):
            msg("Great copying success!")

        def onCopyFailure(failure):
            err("Meh, copy fail.")
            return failure

        copy_list = []

        # First, we need to copy the stuff to the das4 clusters we want to use to run the experiment
        for host in self._config['head_nodes']:
            pp = OneShotProcessProtocol()
            experiment_dir = self._config['workspace_dir']
            args = ("/usr/bin/rsync", "-avz", "--recursive", "--exclude=.git*",
                    "--exclude=.svn", "--delete-excluded",
                    experiment_dir + '/', ":".join((host, self._remote_workspace_dir + '/')
                                                   ))
            msg("Running: %s " % ' '.join(args))
            reactor.spawnProcess(pp, args[0], args)

            copy_list.append(pp.getDeferred())

        d = gatherResults(copy_list, consumeErrors=True)
        d.addCallbacks(onCopySuccess, onCopyFailure)

    def runRemoteSetupScript(self):
        def onSetupSuccess(ignored):
            msg("Remote setup successful!")

        def onSetupFailure(failure):
            return failure

        remote_cmd_list = []
        for host in self._config['head_nodes']:
            final_cmd = path.join(self._remote_workspace_dir, self._config['remote_setup_cmd'])
            d = runRemoteCMD(host, final_cmd)
            remote_cmd_list.append(d)
        remote_cmd_dlist = DeferredList(remote_cmd_list, fireOnOneErrback=True)
        remote_cmd_dlist.addCallbacks(onSetupSuccess, onSetupFailure)
        return remote_cmd_dlist

    def spawnTracker(self):
        def onTrackerFailure(failure):
            err("Tracked died, stopping experiment.")
            return failure

        cmd = self._config['tracker_cmd']
        if self._config.as_bool("tracker_run_local"):
            msg("Spawning local tracker with:", cmd)
            pp = OneShotProcessProtocol()
            args = cmd.split(' ', 1)
            reactor.spawnProcess(pp, args[0], args)
            d = pp.getDeferred()
        else:
            msg("Spawning remote tracker on head node with:", cmd)
            final_cmd = path.join(self._remote_workspace_dir, cmd)
            host = self._config['head_nodes'][0]
            d = runRemoteCMD(host, final_cmd)

        d.addErrback(onTrackerFailure)

    def runLocalSetup(self):
        def onLocalSetupSuccess(ignored):
            msg("Local setup script finished.")

        def onLocalSetupFailure(failure):
            return failure
        pp = OneShotProcessProtocol()
        args = self._config['local_setup_cmd'].split()
        args = ['pwd']
        reactor.spawnProcess(pp, args[0], args)

        d = pp.getDeferred()
        d.addCallbacks(onLocalSetupSuccess, onLocalSetupFailure)
        return d

    def spawnLocalInstances(self):
        def onLocalInstanceSuccess(ignored, ignored2):
            msg("Local instances ended successfully")

        def onLocalInstanceFailure(failure):
            err("Meh, local instance spawning failed.")
            return failure

        # process_guard_file = open(mkstemp()[1], 'w')
        # for i in xrange(0,self._config.as_int('local_instances_amount')):
        #     process_guard_file.write(self._config['local_setup_cmd']+'\n')
        pp = OneShotProcessProtocol()

        args = self._config['local_instance_cmd'].split()
        reactor.spawnProcess(pp, args[0], args)
        d = pp.getDeferred()
        d.addBoth(onLocalInstanceSuccess, onLocalInstanceFailure)
        return d

    def spawnRemoteInstances(self):
        remote_instance_list = []
        final_cmd = path.join(self._remote_workspace_dir, self._config['remote_instance_cmd'])
        for host in self._config['head_nodes']:
            remote_instance_list.append(runRemoteCMD(host, final_cmd))
        return gatherResults(remote_instance_list, consumeErrors=True)

    @inlineCallbacks
    def runRemote(self):
        def onExperimentFinished(_):
            msg("Experiment finished successfully!, collecting data")
            # TODO: Actually collect data
            reactor.stop()

        def onExperimentFailed(failure):
            err("Experiment execution failed on remote nodes, exiting")
            return failure

        try:
            msg("Syncing workspaces on remote head nodes...")
            yield self.copyWorkspaceToHeadNodes()
            msg("Running remote setup scripts on all head nodes")
            # Ok, now that the head nodes have all the necessary files we can run the setup script
            yield self.runRemoteSetupScript()
            msg("Spawning remote instances")
            d = self.spawnRemoteInstances()
            d.addCallbacks(onExperimentFinished, onExperimentFailed)
            yield d
            msg("Remote instances died")
        except Exception, e:
            raise RuntimeError("Remote execution failed with: %s", e)

    @inlineCallbacks
    def runLocal(self):
        try:
            msg('Running local setup scripts')
            yield self.runLocalSetup()
            msg('Spawning tracker')
            self.spawnTracker()
            msg('Spawning local instances')
            yield self.spawnLocalInstances()
            msg('Local instances died')
        except Exception, e:
            raise RuntimeError("Local execution failed with: %s" % e)

    def run(self):
        def onExperimentSucceeded(_):
            msg("experiment suceeded")

        def onExperimentFailed(failure):
            err("Experiment execution failed, exiting with error.")
            err(failure)
            if reactor.running:
                reactor.stop()
            reactor.addSystemEventTrigger('after', 'shutdown', sys.exit, 1)

        chdir(self._experiment_dir)

        d1 = self.runRemote()
        d2 = self.runLocal()

        d = gatherResults((d1, d2), consumeErrors=True)
        d.addCallbacks(onExperimentSucceeded, onExperimentFailed)
        return d

class OneShotProcessProtocol(ProcessProtocol):
    def __init__(self, *k, **w):
        self._d = Deferred()

    def processExited(self, reason):
        msg("Process exited with reason: %s" % reason)
        msg("exit code %s" % reason.value.exitCode)
        if reason.value.exitCode:
            self._d.errback(reason)
        else:
            self._d.callback(None)

    def outReceived(self, data):
        msg("STDOUT: %s" % data.strip())

    def errReceived(self, data):
        msg("STDERR: %s" % data.strip())

    def getDeferred(self):
        return self._d

#
# run.py ends here
