import json
import logging
from time import time
from collections import Iterable
from os import environ, path, makedirs, chdir

from twisted.internet import reactor
from twisted.internet.threads import deferToThread
from twisted.protocols.basic import LineReceiver

from gumby.sync import stop_reactor
from gumby.scenario import ScenarioRunner
from gumby.modules.experiment_module import ExperimentModule


def experiment_callback(name=None):
    """
    This decorator is used to mark members that are callable from a scenario file. It must be the outer most decorator
    of a method. Optionally a name can be specified to make the decorated method available in the scenario file under a
    different name.

    @experiment_callback
    def my_method_x(self):
        ...

    @experiment_callback()
    def my_method_y(self):
        ...

    @experiment_callback("my_method_a")
    def my_method_z(self):
        ...

    :param name: (optional) the name under which to register the decorated method with the scenario runner.
    """
    def experiment_callback_wrapper(f):
        f.register_as_callback = name if name is not None and not callable(name) else f.__name__
        return f
    if callable(name):
        return experiment_callback_wrapper(name)
    else:
        return experiment_callback_wrapper


class ExperimentClient(object, LineReceiver):
    # Allow for 4MB long lines (for the json stuff)
    MAX_LENGTH = 2 ** 22

    def __init__(self, vars):
        super(ExperimentClient, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)

        self.state = "id"
        self.my_id = None
        self.vars = vars
        self.all_vars = {}
        self.time_offset = None
        self.scenario_runner = ScenarioRunner()
        self.scenario_runner.preprocessor_callbacks["module"] = self._preproc_module
        self.loaded_experiment_module_classes = []
        self.experiment_modules = []
        self._stats_file = None
        self.scenario_file = environ.get("SCENARIO_FILE", None)

        self.register_callbacks(self)

        if self.scenario_file is None:
            self._logger.error("No scenario file defined, starting empty experiment")
        else:
            if not path.exists(self.scenario_file) and not path.isabs(self.scenario_file):
                self._logger.info("Scenario file %s not found, attempting scenario file in experiment dir",
                                  self.scenario_file)
                self.scenario_file = path.join(environ['EXPERIMENT_DIR'], self.scenario_file)
            if path.exists(self.scenario_file):
                self.scenario_runner.add_scenario(self.scenario_file)
            else:
                self._logger.info("Scenario file %s not found", self.scenario_file)

    def connectionMade(self):
        self._logger.debug("Connected to the experiment server")
        self.sendLine("time:%f" % time())

        self.state = "id"

    def lineReceived(self, line):
        try:
            pto = 'proto_' + self.state
            state_handler = getattr(self, pto)
        except AttributeError:
            self._logger.error('Callback %s not found', self.state)
            stop_reactor()
        else:
            self.state = state_handler(line)
            if self.state == 'done':
                self.transport.loseConnection()

    def on_id_received(self):
        self.scenario_runner.set_peernumber(self.my_id)

        my_dir = path.join(environ['OUTPUT_DIR'], str(self.my_id))
        if path.exists(my_dir):
            self._logger.warning("Output directory already exists, should you clean before experiment? (%s)", my_dir)
        else:
            makedirs(my_dir)
        chdir(my_dir)
        self._stats_file = open("statistics.log", 'w')

        for module in self.experiment_modules:
            module.on_id_received()

        for key, val in self.vars.iteritems():
            self.sendLine("set:%s:%s" % (key, val))

    def on_all_vars_received(self):
        pass

    def start_experiment(self):
        self.scenario_runner.run()

    def get_peer_id(self, ip, port):
        port = int(port)
        for peer_id, peer_dict in self.all_vars.iteritems():
            if peer_dict['host'] == ip and int(peer_dict['port']) == port:
                return peer_id

        self._logger.error("Could not get_peer_id for %s:%s", ip, port)

    def get_peer_ip_port_by_id(self, peer_id):
        if str(peer_id) in self.all_vars:
            return str(self.all_vars[str(peer_id)]['host']), self.all_vars[str(peer_id)]['port']

    def get_peers(self):
        return self.all_vars.keys()

    #
    # Protocol state handlers
    #

    def proto_id(self, line):
        # We should get a line such as:
        # id:SOMETHING
        maybe_id, id = line.strip().split(':', 1)
        if maybe_id == "id":
            self.my_id = int(id)
            self._logger.debug('Got assigned id: %s', id)
            d = deferToThread(self.on_id_received)
            d.addCallback(lambda _: self.sendLine("ready"))
            return "all_vars"
        else:
            self._logger.error("Received an unexpected string from the server, closing connection")
            return "done"

    def proto_all_vars(self, line):
        self._logger.debug("Got experiment variables")

        self.all_vars = json.loads(line)
        self.time_offset = self.all_vars[str(self.my_id)]["time_offset"]
        self.on_all_vars_received()

        self.sendLine("vars_received")
        return "go"

    def proto_go(self, line):
        self._logger.debug("Got GO signal")
        if line.strip().startswith("go:"):
            start_delay = max(0, float(line.strip().split(":")[1]) - time())
            self._logger.info("Starting the experiment in %f secs.", start_delay)
            reactor.callLater(start_delay, self.start_experiment)
            self.factory.stopTrying()
            self.transport.loseConnection()

    def register(self, target):
        """
        Takes an object (usually an instance of ExperimentModule) and scans it for members that have the
        experiment_callback decorator applied. Any such members will be registered with the scenario runner.

        :param target: The object to scan for experiment callback decorated members.
        """
        if target in self.experiment_modules:
            return
        self.experiment_modules.append(target)

        # We have to be careful not to getattr on members that are @property decorated. Besides them not being
        # callbacks anyways, they trigger the python descriptors that invoke the @property magic. We would invoke the
        # getter. So we filter the contents of our target.
        member_names = [name for name in dir(target) if type(getattr(target.__class__, name, None)).__name__ !=
                        "property"]
        for member in [getattr(target, key) for key in member_names]:
            if not (callable(member) and hasattr(member, "register_as_callback")):
                continue
            else:
                self.scenario_runner.register(member, name=member.register_as_callback)

    @experiment_callback
    def echo(self, *argv):
        self._logger.info("%s ECHO %s", self.my_id, ' '.join(argv))

    @experiment_callback
    def annotate(self, message):
        self._stats_file.write('%.1f %s %s %s\n' % (time(), self.my_id, "annotate", message))

    @experiment_callback
    def peertype(self, peer_type):
        self._stats_file.write('%.1f %s %s %s\n' % (time(), self.my_id, "peertype", peer_type))

    @experiment_callback
    def stop(self):
        stop_reactor()

    def print_dict_changes(self, name, prev_dict, cur_dict):
        """
        Prints the changes in a dict with respect to another dict
        :param name: the name to use when writing dict chanves to the stats file
        :param prev_dict: the first dict to use for comparison
        :param cur_dict: the seconds dict to use for comparison
        :return: a dict that is equivalent to cur_dict
        """
        def get_changed_values(prev_dict, cur_dict):
            new_values = {}
            changed_values = {}
            if cur_dict:
                for key, value in cur_dict.iteritems():
                    # convert key to make it printable
                    if not isinstance(key, (basestring, int, long, float)):
                        key = str(key)

                    # if this is a dict, recursively check for changed values
                    if isinstance(value, dict):
                        converted_dict, changed_in_dict = get_changed_values(prev_dict.get(key, {}), value)

                        new_values[key] = converted_dict
                        if changed_in_dict:
                            changed_values[key] = changed_in_dict

                    # else convert and compare single value
                    else:
                        if not isinstance(value, (basestring, int, long, float, Iterable)):
                            value = str(value)

                        new_values[key] = value
                        if prev_dict.get(key, None) != value:
                            changed_values[key] = value

            return new_values, changed_values

        new_values, changed_values = get_changed_values(prev_dict, cur_dict)
        if changed_values:
            self._stats_file.write('%.1f %s %s %s\n' % (time(), self.my_id, name, json.dumps(changed_values)))
            self._stats_file.flush()
            return new_values
        return prev_dict

    def _preproc_module(self, filename, line_number, line):
        """
        Handler for preprocessor directive 'module'. It invokes the python import built-in to find the module.

        Without a fully qualified name:

        &module multichain_module
        Will attempt to find multichain_module.py on the python path and import it. (The python path should be set by
        launch_scenario to include the experiment dir, tribler dir and gumby itself)

        With a fully qualified name:

        &module gumby.module.tribler_module.TriblerModule
        Will attempt to find gumby.module.tribler_module on the python path and import from it TriblerModule.

        &module gumby.module.tribler_module
        Will attempt to find gumby.module.tribler_module on the python path and import everything from it

        The import is scanned for subclasses of ExperimentModule. Any such class that is not loaded yet will have its
        on_module_load class method invoked if it exists.

        :param filename: The file where the preprocessor directive was invoked
        :param line_number: The line number where the preprocessor directive was invoked
        :param line: The text that remained on the line after the prprocessor directive
        """

        # First detect if it is a simple or fully qualified name
        (modulename, _, classname) = line.rpartition('.')
        try:
            if modulename is None or modulename == "":
                stuff = __import__(classname)
            else:
                try:
                    stuff = __import__(modulename, fromlist=[classname])
                except:
                    # Perhaps the user specified a qualified module name, not class name. So import it as a module.
                    stuff = __import__(line)
        except:
            self._logger.error("Unable to import %s (from %s:%d)", line, filename, line_number, exc_info=True)
            return

        # If something was found, scan it for: Classes, that are of ExperimentModule, are not ExperimentModule itself
        # and have not been loaded previously.
        for item in [getattr(stuff, item_key) for item_key in dir(stuff)]:
            if not isinstance(item, type) or \
                    not issubclass(item, ExperimentModule) or \
                    item is ExperimentModule or \
                    item in self.loaded_experiment_module_classes:
                continue

            # This class matches the criteria, load it and invoke the on_module_load class method if it exists.
            self.loaded_experiment_module_classes.append(item)
            if hasattr(item, "on_module_load") and callable(item.on_module_load):
                item.on_module_load(self)