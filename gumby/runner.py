#!/usr/bin/env python3
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

from os import path, chdir, environ, makedirs, listdir, remove
from shutil import rmtree
import logging
import sys

from twisted.internet import reactor
from twisted.internet.defer import Deferred, setDebugging, gatherResults, succeed
from twisted.internet.protocol import ProcessProtocol


from .settings import configToEnv, loadConfig
from .sshclient import runRemoteCMD
setDebugging(True)


class ExperimentRunner():

    def __init__(self, conf_path):
        self._logger = logging.getLogger(self.__class__.__name__)

        config = loadConfig(conf_path)
        self._cfg_path = conf_path
        self._cfg = config
        self._remote_workspace_dir = path.join(config['remote_workspace_dir'], "Experiment_" + path.basename(config['experiment_name']))
        # TODO: check if the experiment dir actually exists
        self._workspace_dir = path.abspath(config['workspace_dir'])
        self._output_dir = path.join(self._workspace_dir, 'output')
        self._env_runner = "scripts/run_in_env.py"

    def logPrefix(self):
        return "ExperimentRunner"

    def copyWorkspaceToHeadNodes(self):
        self._logger.info("Syncing workspaces on remote head nodes...")

        def onCopySuccess(ignored):
            self._logger.info("Great copying success!")

        def onCopyFailure(failure):
            self._logger.error("Meh, copy fail.")
            return failure

        def onSingleCopyFailure(failure, host):
            self._logger.error("Failed to synchronize the workspace to the remote host: %s.", host)
            return failure

        copy_list = []

        # First, we need to copy the stuff to the das4 clusters we want to use to run the experiment
        for host in self._cfg['head_nodes']:
            pp = OneShotProcessProtocol("Rsync to remote %s" % host)
            workspace_dir = self._cfg['workspace_dir']
            args = ("/usr/bin/rsync", "-az", "--recursive", "--exclude=.git*",
                    "--exclude=.svn", "--exclude=local", "--exclude=output", "--delete-excluded", "--delete-during",
                    workspace_dir + '/', ":".join((host, self._remote_workspace_dir + '/')
                                                  ))
            self._logger.info("Running: %s ", ' '.join(args))
            reactor.spawnProcess(pp, args[0], args)

            copy_list.append(pp.getDeferred().addErrback(onSingleCopyFailure, host))

        d = gatherResults(copy_list, consumeErrors=True)
        d.addCallbacks(onCopySuccess, onCopyFailure)
        return d

    def collectOutputFromHeadNodes(self):
        self._logger.info("Syncing output data back from head nodes...")

        def onCopySuccess(_):
            self._logger.info("Great copying success!")

        def onCopyFailure(failure):
            self._logger.error("Failed to collect the ouput data from the remote nodes.")
            return failure

        def onSingleCopyFailure(failure, host):
            self._logger.error("Failed to collect the ouput data from the remote host: %s.", host)
            return failure

        copy_list = []

        try:
            makedirs(self._output_dir)
        except OSError:
            pass

        for host in self._cfg['head_nodes']:
            pp = OneShotProcessProtocol("Rsync from remote %s" % host)
            args = ("/usr/bin/rsync", "-az", "--recursive", "--exclude=.git*",
                    "--exclude=.svn", "--exclude=local", "--delete-excluded", "--delete-during",
                    ":".join((host, self._remote_workspace_dir + '/output/')),
                    path.join(self._workspace_dir, "output", host) + "/"
                    )
            self._logger.info("Running: %s ", ' '.join(args))
            reactor.spawnProcess(pp, args[0], args)

            copy_list.append(pp.getDeferred().addErrback(onSingleCopyFailure, host))

        d = gatherResults(copy_list, consumeErrors=True)
        d.addCallbacks(onCopySuccess, onCopyFailure)
        return d

    def spawnTracker(self):
        def onTrackerFailure(failure):
            self._logger.error("Tracked died, stopping experiment.")
            return failure

        cmd = self._cfg['tracker_cmd']

        # TODO: optionally stop the experiment if the tracker dies (now it always stops)
        if cmd:
            if self._cfg.as_bool("tracker_run_local"):
                self._logger.info("Spawning local tracker with: %s", cmd)
                pp = OneShotProcessProtocol()
                args = cmd.split(' ', 1)
                reactor.spawnProcess(pp, args[0], args, env=None)  # Inherit env from parent
                d = pp.getDeferred()
            else:
                self._logger.info("Spawning remote tracker on head node with: %s", cmd)
                final_cmd = path.join(self._remote_workspace_dir, cmd)
                host = self._cfg['head_nodes'][0]
                d = runRemoteCMD(host, final_cmd)

            d.addErrback(onTrackerFailure)

    def spawnConfigServer(self):
        def onConfServerFailure(failure):
            self._logger.error("Config server died, stopping experiment.")
            return failure

        cmd = self._cfg['config_server_cmd']
        if self._cfg.as_bool("tracker_run_local"):
            self._logger.info("Spawning local config server with: %s", cmd)
            pp = OneShotProcessProtocol("LOCAL_CONFIG_SERVER")
            args = cmd.split(' ', 1)
            reactor.spawnProcess(pp, args[0], args, env=None)  # Inherit env from parent
            d = pp.getDeferred()
        else:
            self._logger.info("Spawning config server on head node with: %s", cmd)
            final_cmd = path.join(self._remote_workspace_dir, cmd)
            host = self._cfg['head_nodes'][0]
            d = runRemoteCMD(host, final_cmd)

        d.addErrback(onConfServerFailure)

    def runLocalSetup(self):
        def onLocalSetupSuccess(ignored):
            self._logger.info("Local setup script finished.")

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
            self._logger.info("Remote setup successful!")

        def onSetupFailure(failure):
            return failure
        if self._cfg['remote_setup_cmd']:
            d = self.runCommandOnAllRemotes(self._cfg['remote_setup_cmd'])
            d.addCallbacks(onSetupSuccess, onSetupFailure)
            return d
        else:
            return succeed(None)

    def runSetupScripts(self):
        self._logger.info("Running local and remote setup scripts")
        return gatherResults((self.runRemoteSetup(), self.runLocalSetup()), consumeErrors=True)

    def runCommand(self, command, remote=False):
        if remote:
            self._logger.info("Remotely running command %s", command)
            return self.runCommandOnAllRemotes(command)
        else:
            self._logger.info("Locally running command %s", command)
            return self.runLocalCommand(command)

    def runLocalCommand(self, command):
        # use the local _env_runner
        env_runner = path.abspath(path.join(path.dirname(__file__), "..", self._env_runner))
        args = [env_runner, self._cfg_path, command]
        pp = OneShotProcessProtocol(command)
        reactor.spawnProcess(pp, env_runner, args, env=self.local_env)  # Inherit env from parent + conf vars
        return pp.getDeferred()

    def runCommandOnAllRemotes(self, command):
        remote_instance_list = []
        # TODO: Allow for other venv dirs to be used by setting the path in the config file.
        # use remote _env_runner
        if self._cfg["use_remote_venv"]:
            python = "$HOME/venv/bin/python"
        else:
            python = "python"
        args = " ".join((python, path.join(self._remote_workspace_dir, 'gumby', self._env_runner), " ", self._cfg_path, " ", command))
        for host in self._cfg['head_nodes']:
            self._logger.info("Executing command in %s: %s", host, args)
            remote_instance_list.append(runRemoteCMD(host, args))
        return gatherResults(remote_instance_list, consumeErrors=True)

    def startTracker(self):
        def onTrackerFailure(failure):
            self._logger.error("Tracker has exited with status: %s", failure.getErrorMessage())
            # TODO: Add a config option to not shut down the experiment when the tracker dies
            reactor.exitCode = 1
            reactor.stop()

        if self._cfg['tracker_cmd']:
            self._tracker_d = self.runCommand(self._cfg['tracker_cmd'], self._cfg.as_bool('tracker_run_remote'))
            self._tracker_d.addErrback(onTrackerFailure)
            d = Deferred()
            reactor.callLater(1, d.callback, None)
            return d
        else:
            return succeed(None)

    def startExperimentServer(self):
        def onConfigServerDied(failure):
            self._logger.error("Config server has exited with status: %s", failure.getErrorMessage())
            # TODO: Add a config option to not shut down the experiment when the config server dies???
            reactor.exitCode = 1
            reactor.stop()

        if self._cfg['experiment_server_cmd']:
            # TODO: This is not very flexible, refactor it to have a background_commands
            # list instead of experiment_server_cmd, tracker_cmd, etc...
            self._config_server_d = self.runCommand(self._cfg['experiment_server_cmd'], self._cfg.as_bool('experiment_server_run_remote'))
            self._config_server_d.addErrback(onConfigServerDied)
            d = Deferred()
            reactor.callLater(1, d.callback, None)
            return d
        else:
            return succeed(None)

    def startInstances(self):
        self._logger.info("Starting local and remote instances")

        def onStartInstancesFailed(failure):
            self._logger.error("Running the experiment instances failed, collecting data before failing.")
            return self.collectOutputFromHeadNodes().addCallback(lambda _: failure)

        if self._cfg['remote_instance_cmd']:
            dr = self._instances_d = self.runCommandOnAllRemotes(self._cfg['remote_instance_cmd'])
        else:
            dr = succeed(None)
        if self._cfg['local_instance_cmd']:
            dl = self.runCommand(self._cfg['local_instance_cmd'])
        else:
            dl = succeed(None)
        return gatherResults([dr, dl], consumeErrors=True).addErrback(onStartInstancesFailed)

    def runPostProcess(self):
        if self._cfg['post_process_cmd']:
            self._logger.info("Post processing collected data")
            return self.runCommand(self._cfg['post_process_cmd'])

    def run(self):
        def onExperimentSucceeded(_):
            self._logger.info("experiment suceeded")
            reactor.stop()

        def onExperimentFailed(failure):
            self._logger.error("Experiment execution failed, exiting with error.")
            self._logger.error(repr(failure))

            if reactor.running:
                reactor.exitCode = 1
                reactor.stop()
            reactor.addSystemEventTrigger('after', 'shutdown', sys.exit, 1)

        chdir(self._workspace_dir)

        # Step 1:
        # Inject all the config options as env variables to give sub-processes easy acces to them.
        self.local_env = environ.copy()
        self.local_env.update(configToEnv(self._cfg))
        self.local_env['LOCAL_RUN'] = 'True'

        # Step 2:
        # Clear output dir before starting.
        if path.exists(self._output_dir):
            for element in listdir(self._output_dir):
                if path.isfile(path.join(self._output_dir, element)):
                    remove(path.join(self._output_dir, element))
                else:
                    rmtree(path.join(self._output_dir, element))

        # Step 3:
        # Sync the working dir with the head nodes
        d = Deferred()
        d.addCallback(lambda _: self.copyWorkspaceToHeadNodes())

        # Step 4:
        # Run the set up script, both locally and in the head nodes
        d.addCallback(lambda _: self.runSetupScripts())

        # Step 5:
        # Start the tracker, either locally or on the first head node of the list.
        d.addCallback(lambda _: self.startTracker())

        # Step 6:
        # Start the config server, always locally if running instances locally as the head nodes are firewalled and
        # can only be reached from the outside trough SSH.
        d.addCallback(lambda _: self.startExperimentServer())

        # Step 7:
        # Spawn both local and remote instance runner scripts, which will connect to the config server and wait for all
        # of them to be ready before starting the experiment.
        d.addCallback(lambda _: self.startInstances())

        # Step 8:
        # Collect all the data from the remote head nodes.
        d.addCallback(lambda _: self.collectOutputFromHeadNodes())

        # Step 9:
        # Extract the data and graph stuff
        d.addCallback(lambda _: self.runPostProcess())

        # TODO: From here onwards
        reactor.callLater(0, d.callback, None)
        # reactor.callLater(60, reactor.stop)

        return d.addCallbacks(onExperimentSucceeded, onExperimentFailed)


class OneShotProcessProtocol(ProcessProtocol):

    def __init__(self, command, *k, **w):
        self._logger = logging.getLogger(self.__class__.__name__)

        self.command = command
        self._stdout_bytes = ''
        self._stderr_bytes = ''
        self._d = Deferred()

    def processExited(self, reason):
        # TODO(emilon): Process self._stdout_bytes, _sterr_bytes before exiting, to make sure no output is lost.
        # self._logger.info('CMD "%s" Process exited with reason: %s', self.command, reason)
        self._logger.info('[%s] exit code %s', self.command, reason.value.exitCode)
        if reason.value.exitCode:
            self._d.errback(reason)
        else:
            self._d.callback(None)

    def outReceived(self, data):
        # we could recv more than 1 line and/or a partial line.
        self._stdout_bytes += data.decode('utf-8')
        remainder = ""
        for line in self._stdout_bytes.splitlines(True):
            if line.endswith('\n'):
                self._logger.info('[%s] OUT: %s', self.command[:20].strip() + "..." if len(self.command) >20 else "",
                                  line.rstrip())
            else:
                # It's a partial line (part of the last one), save it to the buffer instead
                remainder = line
        self._stdout_bytes = remainder

    def errReceived(self, data):
        self._stderr_bytes += data.decode('utf-8')
        remainder = ""
        for line in self._stderr_bytes.splitlines(True):
            if line.endswith('\n'):
                self._logger.info('[%s] ERR: %s', self.command[:20].strip() + "..." if len(self.command) >20 else "",
                                  line.rstrip())
            else:
                # It's a partial line (part of the last one), save it to the buffer instead
                remainder = line
        self._stderr_bytes = remainder

    def getDeferred(self):
        return self._d

#
# run.py ends here
