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
from os import path, chdir, environ

from twisted.python.log import err, msg, Logger
from twisted.internet.defer import Deferred, setDebugging, gatherResults, succeed

from twisted.internet.protocol import ProcessProtocol
from twisted.internet import reactor

from .sshclient import runRemoteCMD

setDebugging(True)


class ExperimentRunner(Logger):

    def __init__(self, config):
        self._cfg = config
        self._remote_workspace_dir = "Experiment_" + path.basename(config['workspace_dir'])
        # TODO: check if the experiment dir actually exists
        self._workspace_dir = path.abspath(config['workspace_dir'])
        self._env_runner = "scripts/run_in_env.sh"

    def logPrefix(self):
        return "ExperimentRunner"

    def copyWorkspaceToHeadNodes(self):
        msg("Syncing workspaces on remote head nodes...")

        def onCopySuccess(ignored):
            msg("Great copying success!")

        def onCopyFailure(failure):
            err("Meh, copy fail.")
            return failure

        copy_list = []

        # First, we need to copy the stuff to the das4 clusters we want to use to run the experiment
        for host in self._cfg['head_nodes']:
            pp = OneShotProcessProtocol()
            workspace_dir = self._cfg['workspace_dir']
            args = ("/usr/bin/rsync", "-avz", "--recursive", "--exclude=.git*",
                    "--exclude=.svn", "--exclude=local", "--delete-excluded",
                    workspace_dir + '/', ":".join((host, self._remote_workspace_dir + '/')
                                                  ))
            msg("Running: %s " % ' '.join(args))
            reactor.spawnProcess(pp, args[0], args)

            copy_list.append(pp.getDeferred())

        d = gatherResults(copy_list, consumeErrors=True)
        d.addCallbacks(onCopySuccess, onCopyFailure)
        return d

    def spawnTracker(self):
        def onTrackerFailure(failure):
            err("Tracked died, stopping experiment.")
            return failure

        cmd = self._cfg['tracker_cmd']

        # TODO: optionally stop the experiment if the tracker dies (now it always stops)
        if cmd:
            if self._cfg.as_bool("tracker_run_local"):
                msg("Spawning local tracker with:", cmd)
                pp = OneShotProcessProtocol()
                args = cmd.split(' ', 1)
                reactor.spawnProcess(pp, args[0], args, env=None)  # Inherit env from parent
                d = pp.getDeferred()
            else:
                msg("Spawning remote tracker on head node with:", cmd)
                final_cmd = path.join(self._remote_workspace_dir, cmd)
                host = self._cfg['head_nodes'][0]
                d = runRemoteCMD(host, final_cmd, self.remote_env)

            d.addErrback(onTrackerFailure)

    def spawnConfigServer(self):
        def onConfServerFailure(failure):
            err("Config server died, stopping experiment.")
            return failure

        cmd = self._cfg['config_server_cmd']
        if self._cfg.as_bool("tracker_run_local"):
            msg("Spawning local config server with:", cmd)
            pp = OneShotProcessProtocol()
            args = cmd.split(' ', 1)
            reactor.spawnProcess(pp, args[0], args, env=None)  # Inherit env from parent
            d = pp.getDeferred()
        else:
            msg("Spawning config server on head node with:", cmd)
            final_cmd = path.join(self._remote_workspace_dir, cmd)
            host = self._cfg['head_nodes'][0]
            d = runRemoteCMD(host, final_cmd, self.remote_env)

        d.addErrback(onConfServerFailure)

    def runLocalSetup(self):
        def onLocalSetupSuccess(ignored):
            msg("Local setup script finished.")

        def onLocalSetupFailure(failure):
            return failure

        if self._cfg['local_setup_cmd']:
            cmd = self._cfg['local_setup_cmd']
            d = self.runLocalCommand(cmd)
            d.addCallbacks(onLocalSetupSuccess, onLocalSetupFailure)
            return d
        else:
            return succeed(None)

    def runRemoteSetup(self):
        def onSetupSuccess(ignored):
            msg("Remote setup successful!")

        def onSetupFailure(failure):
            return failure
        if self._cfg['remote_setup_cmd']:
            d = self.runCommandOnAllRemotes(self._cfg['remote_setup_cmd'])
            d.addCallbacks(onSetupSuccess, onSetupFailure)
            return d
        else:
            return succeed(None)

    def runSetupScripts(self):
        msg("Running local and remote setup scripts")
        return gatherResults((self.runRemoteSetup(), self.runLocalSetup()), consumeErrors=True)

    def runCommand(self, command, remote=False):
        if remote:
            msg("Remotely running command", command)
            return self.runCommandOnAllRemotes(command)
        else:
            msg("Locally running command", command)
            return self.runLocalCommand(command)

    def runLocalCommand(self, command):
        # use the local _env_runner
        env_runner = path.abspath(path.join(path.dirname(__file__), "..", self._env_runner))
        args = [env_runner, command]
        pp = OneShotProcessProtocol()
        reactor.spawnProcess(pp, env_runner, args, env=self.local_env)  # Inherit env from parent + conf vars
        return pp.getDeferred()

    def runCommandOnAllRemotes(self, command):
        remote_instance_list = []
        # use remote _env_runner
        args = path.join(self._remote_workspace_dir, 'gumby', self._env_runner) + " " + command
        for host in self._cfg['head_nodes']:
            msg("Executing command in %s: %s" % (host, args))
            remote_instance_list.append(runRemoteCMD(host, args, self.remote_env))
        return gatherResults(remote_instance_list, consumeErrors=True)

    def startTracker(self):
        def onTrackerFailure(failure):
            err("Tracker has died.")
            # TODO: Add a config option to not shut down the experiment when the tracker dies
            reactor.stop()
        if self._cfg['tracker_cmd']:
            self._tracker_d = self.runCommand(self._cfg['tracker_cmd'], self._cfg.as_bool('tracker_run_remote'))
            self._tracker_d.addErrback(onTrackerFailure)
            d = Deferred()
            reactor.callLater(1, d.callback, None)
            return d
        else:
            return succeed(None)

    def startConfigServer(self):
        def onConfigServerFailure(failure):
            err("Config server has died.")
            # TODO: Add a config option to not shut down the experiment when the config server dies???
            reactor.stop()
        if self._cfg['config_server_cmd']:
            # Only run it on the DAS head node if we aren't using systemtap.
            self._config_server_d = self.runCommand(self._cfg['config_server_cmd'], not self._cfg.as_bool('use_local_systemtap'))
            self._config_server_d.addErrback(onConfigServerFailure)
            d = Deferred()
            reactor.callLater(1, d.callback, None)
            return d
        else:
            return succeed(None)

    def startInstances(self):
        msg("Starting local and remote instances")
        if self._cfg['remote_instance_cmd']:
            dr = self._instances_d = self.runCommandOnAllRemotes(self._cfg['remote_instance_cmd'])
        else:
            dr = succeed(None)
        if self._cfg['local_instance_cmd']:
            dl = self.runCommand(self._cfg['local_instance_cmd'])
        else:
            dl = succeed(None)
        return gatherResults([dr, dl], consumeErrors=True)

    def runPostProcess(self):
        if self._cfg['post_process_cmd']:
            msg("Post processing collected data")
            return self.runCommand(self._cfg['post_process_cmd'])

    def run(self):
        def onExperimentSucceeded(_):
            msg("experiment suceeded")
            reactor.stop()

        def onExperimentFailed(failure):
            err("Experiment execution failed, exiting with error.")
            err(failure)
            if reactor.running:
                reactor.stop()
            reactor.addSystemEventTrigger('after', 'shutdown', sys.exit, 1)

        chdir(self._workspace_dir)

        # Step 1: (Not anymore, directly exported to the subproces' environ)
        # Write the experiment config variables to a file sourceable by a shell script
        # with open(path.join(self._workspace_dir,"experiment_vars.sh"), 'w') as vars_f:
        # vars_f.write("# Auto generated file, do not modify\n")
        # for key, val in self._cfg.iteritems():
        # vars_f.write('export %s="%s"\n' % (key.upper(), val))

        # Step 1:
        # Inject all the config options as env variables to give suprocesses easy acces to them.
        self.local_env = environ.copy()
        self.local_env.update({name.upper(): path.expanduser(path.expandvars(str(val))) for name, val in self._cfg.iteritems()})
        self.remote_env = {name.upper(): str(val) for name, val in self._cfg.iteritems()}

        # Step 2:
        # Sync the working dir with the head nodes
        d = Deferred()
        d.addCallback(lambda _: self.copyWorkspaceToHeadNodes())

        # Step 3:
        # Run the set up script, both locally and in the head nodes
        d.addCallback(lambda _: self.runSetupScripts())

        # Step 4:
        # Start the tracker, either locally or on the first head node of the list.
        d.addCallback(lambda _: self.startTracker())

        # Step 5:
        # Start the config server, always locally if running instances locally as the head nodes are firewalled and
        # can only be reached from the outside trough SSH.
        d.addCallback(lambda _: self.startConfigServer())

        # Step 6:
        # Spawn both local and remote instance runner scripts, which will connect to the config server and wait for all
        # of them to be ready before starting the experiment.
        d.addCallback(lambda _: self.startInstances())

        # Step 7:
        # Collect all the data from the remote head nodes.
        # TODO: implement this.

        # Step 8:
        # Extract the data and graph stuff
        d.addCallback(lambda _: self.runPostProcess())

        # TODO: From here onwards
        reactor.callLater(0, d.callback, None)
        # reactor.callLater(60, reactor.stop)

        return d.addCallbacks(onExperimentSucceeded, onExperimentFailed)

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
