#!/usr/bin/env python3
# Mircea Bardac
# Rewritten by Elric Milon (Dec. 2012 and Aug. 2013)

import json
from glob import iglob
from math import ceil
from os import (R_OK, access, errno, getpgid, getpid, kill, killpg, makedirs, mkdir, path, setsid, sysconf,
                sysconf_names)
from signal import SIGKILL, SIGTERM, signal
from subprocess import Popen
from time import sleep, time

from psutil import Process, AccessDenied, NoSuchProcess

OK_EXIT_CODE = 0
TIMEOUT_EXIT_CODE = 3
COMMANDS_FAILED_EXIT_CODE = 5


class PGPopen(Popen):

    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        super(PGPopen, self).__init__(cmd, *args, **kwargs)


class ResourceMonitor(object):
    # adapted after http://stackoverflow.com/questions/276052/how-to-get-current-cpu-and-ram-usage-in-python

    def __init__(self, output_dir, commands):
        """Create new ResourceMonitor instance."""

        self.cmd_counter = 0
        self.pid_dict = {}

        self.failed_commands = {}

        self.files = []
        self.output_dir = output_dir

        self.pgid_list = []

        self.nr_commands = len(commands)
        for command in commands:
            self.run(command)

        self.pid_list = []
        self.pid_list.extend(self.pid_dict.keys())
        self.ignore_pid_list = []
        self.ignore_pid_list.append(getpid())

        self.last_died = False

        self.verbose = True

    def prune_pid_list(self):
        """
        Remove all finished processes from pid_dict and pid_list.
        """
        def pid_exists(pid):
            """Check whether pid exists in the current process table."""
            # From: http://stackoverflow.com/questions/568271/check-if-pid-is-not-in-use-in-python
            if pid < 0:
                return False
            try:
                kill(pid, 0)
            except OSError as e:
                return e.errno == errno.EPERM
            else:
                return True
        pids_to_remove = set()
        for pid, popen in self.pid_dict.items():
            if popen.poll() is not None:
                pids_to_remove.add(pid)

        for pid in self.pid_list:
            if not pid_exists(pid):
                pids_to_remove.add(pid)

        for pid in pids_to_remove:
            if pid in self.pid_dict:
                p = self.pid_dict.pop(pid)
                status = p.poll()
                if self.verbose:
                    print("Command:\n\t %s\n\t exited with status: %d" % (p.cmd, status))
                if status:
                    self.failed_commands[pid] = (p.cmd, status)
            if pid in self.pid_list:
                self.pid_list.remove(pid)

        if not self.pid_list and pids_to_remove:  # If the pid list is empty and we have removed any PID, it means we can exit as no more processes will appear.
            self.last_died = True

    def get_raw_stats(self):
        for pid in self.pid_list:
            try:
                if False:
                    status = "9932 (bash) S 1 9932 9932 0 -1 8192 1330 25068 0 12 1 0 21 7 20 0 1 0 873934607 112930816 2 18446744073709551615 1 1 0 0 0 0 65536 4 65538 18446744073709551615 0 0 17 0 0 0 0 0 0"
                    lines = [
                        "rchar: 2012\n",
                        "wchar: 0\n",
                        "syscr: 7\n",
                        "syscw: 0\n",
                        "read_bytes: 0\n",
                        "write_bytes: 0\n",
                        "cancelled_write_bytes: 0\n",
                    ]
                else:
                    status = open('/proc/%s/stat' % pid, 'r').read()[:-1]  # Skip the newline
                    lines = open('/proc/%s/io' % pid, 'r').readlines()

                stats = [status]
                for line in lines:
                    try:
                        stats.append(line.split(': ')[1][:-1])  # Skip the newline

                    except Exception as e:
                        print("Got exception while reading/splitting line:")
                        print(e)
                        print("Line contents are: %s" % line)
                yield ' '.join(stats)

            except IOError:
                self.pid_list.remove(pid)
                if not self.pid_list:
                    self.last_died = True

    def get_network_stats(self):
        # Skip first two lines.
        network = open('/proc/net/dev').readlines()[2:]
        for line in network:
            # Remove unnecessary whitespace within line.
            shortline = ' '.join(line.split())
            # Strip to remove leading space.
            # and remove ':' after network device name.
            yield shortline.replace(':', '').strip()

    def is_everyone_dead(self):
        return self.last_died or not self.pid_list

    def update_pid_tree(self):
        """Update the list of PIDs contained in the process group"""
        for pid_dir in iglob('/proc/[1-9]*'):
            pid = int(pid_dir.split('/')[-1])
            if pid in self.pid_list or pid in self.ignore_pid_list:
                continue

            stat_file = path.join(pid_dir, 'stat')
            io_file = path.join(pid_dir, 'io')
            if access(stat_file, R_OK) and access(io_file, R_OK):
                pgrp = int(open(stat_file, 'r').read().split()[4])  # 4 is PGRP
                if pgrp in self.pgid_list:
                    self.pid_list.append(pid)
                else:
                    self.ignore_pid_list.append(pid)

    def run(self, cmd):
        if self.output_dir:
            output_filename = self.output_dir + "/%05d.out" % self.cmd_counter
            error_filename = self.output_dir + "/%05d.err" % self.cmd_counter

            stdout = open(output_filename, "w")
            stderr = open(error_filename, "w")

            self.files.append(stdout)
            self.files.append(stderr)
        else:
            stdout = stderr = None

        print("Starting #%05d: %s" % (self.cmd_counter, cmd))
        if stdout:
            stdout.flush()
        p = PGPopen(cmd, shell=True, stdout=stdout, stderr=stderr, close_fds=True, env=None, preexec_fn=setsid)
        self.pid_dict[p.pid] = p
        self.pgid_list.append(getpgid(p.pid))

        self.cmd_counter = self.cmd_counter + 1

    def terminate(self):
        for file in self.files:
            try:
                file.flush()
                file.close()
            except:
                pass

        self.prune_pid_list()
        for id, p in self.pid_dict.items():
            print("TERMinating group. Still %i process(es) running:" % len(self.pid_dict))
            for pid in self.get_pid_list():
                try:
                    with open("/proc/%d/cmdline" % pid, 'r') as cmd:
                        print(" - %s" % cmd.read())
                except IOError:
                    pass
            killpg(id, SIGTERM)  # kill the entire process group, we are ignoring the SIGTERM.

        if self.pid_dict:
            sleep(0.1)
            self.prune_pid_list()
            if self.pid_dict:
                    print("Some processes survived SIGTERM.")
                    print("Nuking the whole thing, have a nice day...")
                    for id, p in self.pid_dict.items():
                        killpg(id, SIGKILL)  # kill the entire process group

    def get_pid_list(self):
        return self.pid_dict.keys()

    def get_failed_commands(self):
        return self.failed_commands.copy()


class ProcessMonitor(object):

    def __init__(self, commands, timeout, interval, output_dir=None, monitor_dir=None, network=False):
        self.start_time = time()
        self.timed_out = False
        self.end_time = self.start_time + timeout if timeout else 0  # Do not time out if time_limit is 0.
        self._interval = interval

        self._rm = ResourceMonitor(output_dir, commands)
        self.monitor_file = None
        self.network_monitor_file = None
        self.fd_file = None
        self.threads_file = None
        self.psutil_process = Process()

        if monitor_dir:
            self.monitor_file = open(monitor_dir + "/resource_usage.log", "w", (1024 ** 2) * 10)  # Set the file's buffering to 10MB
            if not path.exists(monitor_dir + "/autoplot"):
                mkdir(monitor_dir + "/autoplot")
            # Set the file's buffering to 10MB
            self.fd_file = open(monitor_dir + "/autoplot/fd_usage.csv", "w", (1024 ** 2) * 10)
            self.fd_file.write("time,pid,Number of file descriptors\n")
            # Set the file's buffering to 10MB
            self.threads_file = open(monitor_dir + "/autoplot/thread_count.csv", "w", (1024 ** 2) * 10)
            self.threads_file.write("time,pid,Number of threads\n")
            # We read the jiffie -> second conversion rate from the os, by dividing the utime
            # and stime values by this conversion rate we will get the actual cpu seconds spend during this second.
            try:
                sc_clk_tck = float(sysconf(sysconf_names['SC_CLK_TCK']))
            except AttributeError:
                sc_clk_tck = 100.0

            try:
                import resource
                pagesize = resource.getpagesize()
            except:
                pagesize = 4 * 1024

            self.monitor_file.write(json.dumps({"sc_clk_tck": sc_clk_tck, 'pagesize': pagesize}) + "\n")

            # If monitoring network, open a separate file.
            if network:
                self.network_monitor_file = open(monitor_dir + "/network_usage.log", "w", (1024 ** 2) * 10)  # Set the file's buffering to 10MB
        # Capture SIGTERM to kill all the child processes before dying
        self.stopping = False
        signal(SIGTERM, self._termTrap)

    def stop(self):
        self.stopping = True
        if self.monitor_file:
            self.monitor_file.close()
        if self.fd_file:
            self.fd_file.close()
        if self.threads_file:
            self.threads_file.close()

        # Check if any process exited with an error code before killing the remaining ones
        failed = self._rm.get_failed_commands()
        self._rm.terminate()
        if failed:
            print("Some processes failed:")
            for pid, (command, exit_code) in failed.items():
                print("  %s (%d) exited value: %d" % (command, pid, exit_code))
            print("Process guard exiting with error")
            return COMMANDS_FAILED_EXIT_CODE
        else:
            return OK_EXIT_CODE

    def _termTrap(self, *argv):
        print("Captured TERM signal")
        if not self.stopping:
            self.stop()

    def monitoring_loop(self):
        check_for_new_processes = 60

        time_start = time()
        sleep_time = self._interval
        last_subprocess_update = time_start
        while not self.stopping:
            timestamp = time()
            r_timestamp = ceil(timestamp / self._interval) * self._interval  # rounding timestamp to nearest interval to try to overlap multiple nodes

            self._rm.prune_pid_list()
            # Look for new subprocesses only once a second and only during the first "check_for_new_processes" seconds
            if (timestamp < time_start + check_for_new_processes) and (timestamp - last_subprocess_update >= 1):
                self._rm.update_pid_tree()
                last_subprocess_update = timestamp

            if self._rm.is_everyone_dead():
                print("All child processes have died, exiting")
                return self.stop()

            elif self.monitor_file:
                next_wake = timestamp + self._interval

                for line in self._rm.get_raw_stats():
                    self.monitor_file.write("%.1f %s\n" % (r_timestamp, line))

                sleep_time = next_wake - timestamp
                if sleep_time < 0:
                    print("Can't keep up with this interval, try a higher value! %s" % sleep_time)
                    return self.stop()

            if self.network_monitor_file:
                for line in self._rm.get_network_stats():
                    self.network_monitor_file.write("%.1f %s\n" % (r_timestamp, line))

            if hasattr(self.psutil_process, 'children'):
                p_children = self.psutil_process.children(recursive=True)
            else:
                p_children = self.psutil_process.get_children(recursive=True)

            if self.fd_file:
                for child_process in p_children:
                    try:
                        if hasattr(self.psutil_process, 'num_fds'):
                            self.fd_file.write("%.1f,%s,%d\n" %
                                               (r_timestamp, child_process.pid, child_process.num_fds()))
                        else:
                            self.fd_file.write("%.1f,%s,%d\n" %
                                               (r_timestamp, child_process.pid, child_process.get_num_fds()))
                    except (AccessDenied, NoSuchProcess):
                        pass  # Just ignore the file descriptors of this invalid process

            if self.threads_file:
                for child_process in p_children:
                    try:
                        # Supports: Linux, Windows, OSX, SunOS
                        # Unsupported: BSD
                        if hasattr(self.psutil_process, 'num_threads'):
                            self.threads_file.write("%.1f,%s,%d\n" %
                                                    (r_timestamp, child_process.pid, child_process.num_threads()))
                        elif hasattr(self.psutil_process, 'get_num_threads'):
                            self.threads_file.write("%.1f,%s,%d\n" %
                                                    (r_timestamp, child_process.pid, child_process.get_num_threads()))
                    except (AccessDenied, NoSuchProcess):
                        pass  # Just ignore the number of threads of this invalid process

            if self.end_time and timestamp > self.end_time:  # if self.end_time == 0 the time out is disabled.
                print("Time out, killing monitored processes.")
                self.timed_out = True
                return self.stop()
            sleep(sleep_time)

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-t", "--timeout",
                      metavar='TIMEOUT',
                      default=0,
                      type=int,
                      help="Hard timeout, after this amount of seconds all the child processes will be killed."
                      )
    parser.add_option("-T", "--fail-on-timeout",
                      action="store_true",
                      default=False,
                      dest="fail_on_timeout",
                      help="Exit with status code 3 when a timeout happens."
                      )
    parser.add_option("-m", "--monitor-dir",
                      metavar='OUTDIR',
                      help="Monitor individual process/thread resource consumption and write the logs in the specified dir.",
                      )
    parser.add_option("-o", "--output-dir",
                      metavar='OUTDIR',
                      help="Capture individual process std{out|err} and write the logs in the specified dir.",

                      )
    parser.add_option("-f", "--commands-file",
                      metavar='COMMANDS_FILE',
                      help="Read this file and spawn a subprocess using each line as the command line."
                      )
    parser.add_option("-c", "--command",
                      metavar='COMMAND',
                      action="append",
                      dest="commands",
                      help="Run this command (can be specified multiple times and in addition of --commands-file)"
                      )
    parser.add_option("-i", "--interval",
                      metavar='FLOAT',
                      default=1.0,
                      type=float,
                      action="store",
                      help="Sample monitoring stats and check processes/threads every FLOAT seconds"
                      )
    parser.add_option("-n", "--network",
                      action="store_true",
                      default=False,
                      help="Monitor network devices."
                      )
    (options, args) = parser.parse_args()
    if not (options.commands_file or options.commands):
        parser.error("Please specify at least one of --command or --commands-file (run with -h to see command usage).")

    if options.commands:
        commands = [cmd.strip() for cmd in options.commands if cmd.strip()]
    else:
        commands = []
    if options.commands_file:
        with open(options.commands_file) as file:
            for cmd in [line.strip() for line in file.read().splitlines()]:
                if cmd and not cmd.startswith('#'):
                    commands.append(cmd)

    if not commands:
        parser.error("Could not collect a list of commands to run.\nMake sure that the commands file is not empty or has all the lines commented out.")

    if options.output_dir and not path.exists(options.output_dir):
        print("making output directory: %s" % options.output_dir)
        makedirs(options.output_dir)

    pm = ProcessMonitor(commands, options.timeout, options.interval, options.output_dir, options.monitor_dir, options.network)
    try:
        exit(pm.monitoring_loop())

    except KeyboardInterrupt as RuntimeError:
        print("Killing monitored processes...")
        pm.stop()
        print("Done.")
    if pm.timed_out and options.fail_on_timeout:
        exit(TIMEOUT_EXIT_CODE)
