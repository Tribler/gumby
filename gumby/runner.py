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
import logging
import sys
from asyncio import CancelledError, create_subprocess_exec, ensure_future, gather, get_event_loop, subprocess, sleep
from contextlib import suppress
from os import path, chdir, environ, makedirs, listdir, remove
from shutil import rmtree

import asyncssh

from .settings import configToEnv, loadConfig


async def runRemoteCMD(host, command):
    async with asyncssh.connect(host) as conn:
        await conn.run(command, check=True)


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
        self._instances_d = None

    async def copyWorkspaceToHeadNodes(self):
        self._logger.info("Syncing workspaces on remote head nodes...")

        coros = []
        # First, we need to copy the stuff to the das4 clusters we want to use to run the experiment
        for host in self._cfg['head_nodes']:
            workspace_dir = self._cfg['workspace_dir']
            args = ("/usr/bin/rsync", "-az", "--recursive", "--exclude=.git*",
                    "--exclude=.svn", "--exclude=local", "--exclude=output", "--delete-excluded", "--delete-during",
                    workspace_dir + '/', ":".join((host, self._remote_workspace_dir + '/')))
            coros.append(ProcessRunner("Rsync to remote %s" % host, args).run())

        for i, result in enumerate(await gather(*coros, return_exceptions=True)):
            if isinstance(result, Exception):
                host = self._cfg['head_nodes'][i]
                self._logger.error("Failed to synchronize the workspace to the remote host: %s.", host)
                raise result

        self._logger.info("Great copying success!")

    async def collectOutputFromHeadNodes(self):
        self._logger.info("Syncing output data back from head nodes...")

        try:
            makedirs(self._output_dir)
        except OSError:
            pass

        coros = []
        for host in self._cfg['head_nodes']:
            args = ("/usr/bin/rsync", "-az", "--recursive", "--exclude=.git*",
                    "--exclude=.svn", "--exclude=local", "--delete-excluded", "--delete-during",
                    ":".join((host, self._remote_workspace_dir + '/output/')),
                    path.join(self._workspace_dir, "output", host) + "/"
                    )
            coros.append(ProcessRunner("Rsync from remote %s" % host, args).run())

        for i, result in enumerate(await gather(*coros, return_exceptions=True)):
            if isinstance(result, Exception):
                host = self._cfg['head_nodes'][i]
                self._logger.error("Failed to collect the ouput data from the remote host: %s.", host)
                raise result

        self._logger.info("Great copying success!")

    async def runLocalSetup(self):
        if self._cfg['local_setup_cmd']:
            cmd = self._cfg['local_setup_cmd']
            await self.runLocalCommand(cmd)
            self._logger.info("Local setup script finished.")

    async def runRemoteSetup(self):
        if self._cfg['remote_setup_cmd']:
            await self.runCommandOnAllRemotes(self._cfg['remote_setup_cmd'])
            self._logger.info("Remote setup successful!")

    async def runSetupScripts(self):
        self._logger.info("Running local and remote setup scripts")
        await self.runRemoteSetup()
        await self.runLocalSetup()

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
        return ProcessRunner(command, args, env=self.local_env).run()

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
            # TODO: let ProcessRunner log the results
            remote_instance_list.append(runRemoteCMD(host, args))
        return gather(*remote_instance_list)

    async def startTracker(self):
        if self._cfg['tracker_cmd']:
            try:
                await self.runCommand(self._cfg['tracker_cmd'], self._cfg.as_bool('tracker_run_remote'))
            except Exception as e:
                self._logger.error("Error while running tracker: %s", e)
                # TODO: Add a config option to not shut down the experiment when the tracker dies
                get_event_loop().exit_code = 1
                get_event_loop().stop()

    async def startExperimentServer(self):
        if self._cfg['experiment_server_cmd']:
            self._logger.info("Starting experiment server")
            try:
                await self.runCommand(self._cfg['experiment_server_cmd'],
                                      self._cfg.as_bool('experiment_server_run_remote'))
            except Exception as e:
                self._logger.error("Error while running config server: %s", e)
                get_event_loop().exit_code = 1
                get_event_loop().stop()

    async def startInstances(self):
        self._logger.info("Starting local and remote instances")

        coros = []
        if self._cfg['remote_instance_cmd']:
            self._instances_d = self.runCommandOnAllRemotes(self._cfg['remote_instance_cmd'])
            coros.append(self._instances_d)
        if self._cfg['local_instance_cmd']:
            coros.append(self.runCommand(self._cfg['local_instance_cmd']))

        try:
            return await gather(*coros)
        except Exception as e:
            self._logger.error("Running the experiment instances failed, collecting data before failing.")
            await self.collectOutputFromHeadNodes()
            raise e

    async def runPostProcess(self):
        if self._cfg['post_process_cmd']:
            self._logger.info("Post processing collected data")
            return await self.runCommand(self._cfg['post_process_cmd'])

    async def run(self):
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
        await self.copyWorkspaceToHeadNodes()

        # Step 4:
        # Run the set up script, both locally and in the head nodes
        await self.runSetupScripts()

        # Step 5:
        # Start the tracker, either locally or on the first head node of the list.
        tracker_task = ensure_future(self.startTracker())
        await sleep(1)

        # Step 6:
        # Start the config server, always locally if running instances locally as the head nodes are firewalled and
        # can only be reached from the outside trough SSH.
        server_task = ensure_future(self.startExperimentServer())
        await sleep(1)

        # Step 7:
        # Spawn both local and remote instance runner scripts, which will connect to the config server and wait for all
        # of them to be ready before starting the experiment.
        await self.startInstances()

        # Step 8:
        # Collect all the data from the remote head nodes.
        await self.collectOutputFromHeadNodes()

        # Cleanup background tasks
        tracker_task.cancel()
        server_task.cancel()
        await tracker_task
        await server_task

        # Step 9:
        # Extract the data and graph stuff
        await self.runPostProcess()

        self._logger.info("Experiment suceeded")


class ProcessRunner:

    def __init__(self, name, command, env=None):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.name = name
        self.command = command
        self.env = env

    async def run(self):
        self._logger.info("Running: %s ", ' '.join(self.command))

        process = await create_subprocess_exec(*self.command, stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE, env=self.env)

        short_name = self.name[:20].strip() + "..." if len(self.name) > 20 else ""
        task_stdout = ensure_future(self.log_stream(process.stdout, f'[{short_name}] OUT: '))
        task_stderr = ensure_future(self.log_stream(process.stderr, f'[{short_name}] ERR: '))

        try:
            await process.wait()
        except CancelledError:
            process.kill()
            await process.wait()

        for task in (task_stdout, task_stderr):
            task.cancel()
            with suppress(CancelledError):
                await task

        self._logger.info(f'[{self.command}] exit code {process.returncode}')

        if process.returncode > 0:
            raise RuntimeError(f'Process {self.name} exited with code {process.returncode}')

    async def log_stream(self, stream, prefix):
        line = await stream.readline()
        while line:
            self._logger.info(prefix + line.rstrip().decode('utf-8'))
            line = await stream.readline()

#
# run.py ends here
