#!/usr/bin/env python3
import logging
from asyncio import CancelledError, create_subprocess_exec, ensure_future, gather, get_event_loop, sleep, subprocess
from contextlib import suppress
from os import chdir, environ, listdir, path, remove
from shutil import rmtree

from gumby.settings import configToEnv, loadConfig


class ExperimentRunner:

    def __init__(self, conf_path):
        self._logger = logging.getLogger(self.__class__.__name__)

        config = loadConfig(conf_path)
        self._cfg_path = conf_path
        self._cfg = config
        # TODO: check if the experiment dir actually exists
        self._workspace_dir = path.abspath(config['workspace_dir'])
        self._output_dir = path.join(self._workspace_dir, 'output')
        self._env_runner = "scripts/run_in_env.py"
        self._instances_d = None

    async def runSetupScripts(self):
        self._logger.info("Running setup scripts")
        if self._cfg['local_setup_cmd']:
            cmd = self._cfg['local_setup_cmd']
            await self.runCommand(cmd)
            self._logger.info("Local setup script finished.")

    def runCommand(self, command):
        # use the local _env_runner
        env_runner = path.abspath(path.join(path.dirname(__file__), "..", self._env_runner))
        args = [env_runner, self._cfg_path, command]
        return ProcessRunner(command, args, env=self.local_env).run()

    async def startExperimentServer(self):
        if self._cfg['experiment_server_cmd']:
            self._logger.info("Starting experiment server")
            try:
                await self.runCommand(self._cfg['experiment_server_cmd'])
            except Exception as e:
                self._logger.error("Error while running config server: %s", e)
                get_event_loop().exit_code = 1
                get_event_loop().stop()

    async def startInstances(self):
        self._logger.info("Starting local instances")

        coros = []
        if self._cfg['local_instance_cmd']:
            coros.append(self.runCommand(self._cfg['local_instance_cmd']))

        try:
            return await gather(*coros)
        except Exception as e:
            self._logger.error("Running the experiment instances failed.")
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

        # Step 4:
        # Run the set up script, both locally and in the head nodes
        await self.runSetupScripts()

        # Step 6:
        # Start the config server, always locally if running instances locally as the head nodes are firewalled and
        # can only be reached from the outside trough SSH.
        server_task = ensure_future(self.startExperimentServer())
        await sleep(1)

        # Step 7:
        # Spawn local instance runner scripts, which will connect to the config server and wait for all
        # of them to be ready before starting the experiment.
        await self.startInstances()

        # Cleanup background tasks
        server_task.cancel()
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
