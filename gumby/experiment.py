import imp
import json
import logging
import os
from asyncio import get_event_loop
from os import chdir, environ, makedirs, path
import sys
from collections import Iterable
from functools import reduce  # pylint: disable=redefined-builtin
from time import time

from gumby.scenario import ScenarioRunner
from gumby.line_receiver import LineReceiver


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


class ExperimentClient(LineReceiver):
    # Allow for 4MB long lines (for the json stuff)
    MAX_LENGTH = 2 ** 22

    def __init__(self, my_vars):
        self._logger = logging.getLogger(self.__class__.__name__)

        self.state = "id"
        self.my_id = None
        self.vars = my_vars
        self.all_vars = {}
        self.server_vars = {}
        self.time_offset = None
        self.scenario_runner = ScenarioRunner()
        self.scenario_runner.preprocessor_callbacks["module"] = self._preproc_module
        self.loaded_experiment_module_classes = []
        self._stats_file = None
        self.scenario_file = environ.get("SCENARIO_FILE", None)
        self.message_callback = None

        # Beware! The ordering of modules is important, specifically on calling the event handlers.
        self.experiment_modules = []

        self.register(self)

        if self.scenario_file is None:
            self._logger.error("No scenario file defined, starting empty experiment")
        else:
            if not path.exists(self.scenario_file) and not path.isabs(self.scenario_file):
                self._logger.warning("Scenario file %s not found, attempting scenario file in experiment dir",
                                  self.scenario_file)
                self.scenario_file = path.join(environ['EXPERIMENT_DIR'], self.scenario_file)
            if path.exists(self.scenario_file):
                self._logger.info("Scenario file found, using %s", self.scenario_file)
                self.scenario_runner.add_scenario(self.scenario_file)
            else:
                self._logger.error("Scenario file %s not found", self.scenario_file)

    def connection_made(self, transport):
        super(ExperimentClient, self).connection_made(transport)
        self._logger.debug("Connected to the experiment server")
        self.send_line(b"time:%f" % time())
        self.state = "id"

    def line_received(self, line):
        try:
            pto = 'proto_' + self.state
            state_handler = getattr(self, pto)
        except AttributeError:
            self._logger.error('Callback %s not found. Stopping event loop.', self.state)
            get_event_loop().stop()
        else:
            self.state = state_handler(line)

    def send_message(self, peer_id, msg_type, msg):
        self.send_line(b"msg:%d:%s:%s" % (peer_id, msg_type, msg))

    def on_id_received(self):
        self.scenario_runner.set_peernumber(self.my_id)

        my_dir = path.join(environ['OUTPUT_DIR'], str(self.my_id))
        if path.exists(my_dir):
            self._logger.warning("Output directory already exists, should you clean before experiment? (%s)", my_dir)
        else:
            makedirs(my_dir)
        chdir(my_dir)
        self._stats_file = open("statistics.log", 'w', buffering=1)

        for module in self.experiment_modules:
            if module is not self:
                module.on_id_received()

        for key, val in self.vars.items():
            self.send_line(b"set:%s:%s" % (key.encode('utf-8'), val.encode('utf-8')))

        self.send_line(b"ready")

    def on_all_vars_received(self):
        for module in self.experiment_modules:
            if module is not self:
                module.on_all_vars_received()

    def start_experiment(self):
        self.scenario_runner.run()

    def get_peer_id(self, ip, port):
        port = int(port)
        for peer_id, peer_dict in self.all_vars.items():
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
        maybe_id, id = line.strip().split(b':', 1)
        if maybe_id == b"id":
            if "PEER_ID" in os.environ:
                self.my_id = int(os.environ["PEER_ID"])
            else:
                self.my_id = int(id)

            self._logger.debug('Got assigned id: %s', self.my_id)
            get_event_loop().run_in_executor(None, self.on_id_received)
            return "all_vars"
        else:
            self._logger.error("Received an unexpected string from the server, closing connection")
            return "done"

    def proto_all_vars(self, line):
        self._logger.debug("Got experiment variables")

        with open("all_vars.txt", "wb") as output_file:
            output_file.write(line)

        all_vars = json.loads(line)
        self.all_vars = all_vars["clients"]
        self.server_vars = all_vars["server"]
        if "PEER_ID" in os.environ:
            # this is a self service run, i.e. debugging a specific gumby experiment (hopefully in an IDE)
            # and since the my_id var was explicitly set it won't match what the server sent... so let's fix that
            self.all_vars[str(self.my_id)] = self.all_vars["0"]

        self.time_offset = self.all_vars[str(self.my_id)]["time_offset"]
        self.on_all_vars_received()

        self.send_line(b"vars_received")
        return "go"

    def proto_go(self, line):
        self._logger.debug("Got GO signal")
        if line.strip().startswith(b"go:"):
            start_delay = max(0, float(line.strip().split(b":")[1]) - time())
            self._logger.info("Starting the experiment in %f secs.", start_delay)
            get_event_loop().call_later(start_delay, self.start_experiment)
            self.factory.stop_reconnecting()
            return "running"

    def proto_running(self, line):
        if line.startswith(b"msg"):
            _, from_peer_id, msg_type, msg = line.strip().split(b':', 3)
            self._logger.debug("Received message with type %s from peer %d: %s",
                               msg_type.decode(), int(from_peer_id), msg.decode())
            if self.message_callback:
                self.message_callback.on_message(int(from_peer_id), msg_type, msg)

        return "running"

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
    def stop(self):
        self._logger.info("Stopping event loop")
        get_event_loop().stop()

    @experiment_callback
    def set(self, variable_name, variable_value):
        """
        Allows the user to set a variable, which may be reused throughout the experiment. The value of the variable
        will be stored as a string. It is up to the experiment programmer to ensure it's converted to the correct
        type in the methods it will be used.

        :param variable_name: the name of the variable.
        :param variable_value: the value of the variable. The value will be stored as a string.
        :return: None
        """
        self.scenario_runner.user_defined_vars[variable_name] = variable_value

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
                for key, value in cur_dict.items():
                    # convert key to make it printable
                    if not isinstance(key, (str, int, float)):
                        key = str(key)

                    # if this is a dict, recursively check for changed values
                    if isinstance(value, dict):
                        converted_dict, changed_in_dict = get_changed_values(prev_dict.get(key, {}), value)

                        new_values[key] = converted_dict
                        if changed_in_dict:
                            changed_values[key] = changed_in_dict

                    # else convert and compare single value
                    else:
                        if not isinstance(value, (str, int, float, Iterable)):
                            value = str(value)

                        new_values[key] = value
                        if prev_dict.get(key, None) != value:
                            changed_values[key] = value

            return new_values, changed_values

        new_values, changed_values = get_changed_values(prev_dict, cur_dict)
        if changed_values:
            self._stats_file.write('%.1f %s %s %s\n' % (time(), self.my_id, name, json.dumps(changed_values)))
            return new_values
        return prev_dict

    @staticmethod
    def local_import(module_name, logger=None):
        """
        Try to perform a local import of a module with a certain name.

        :param module_name: the fully qualified module path
        :return: the imported module or Non
        """
        if module_name in sys.modules and sys.modules[module_name]:
            return sys.modules[module_name]
        import_exception = None
        try:
            # Can raise ImportError when module_name cannot be imported
            __import__(module_name, level=0)
            # Can raise Attribute error if module_name wasn't loaded after all
            if sys.modules[module_name]:
                # The module can still be unloaded
                return sys.modules[module_name]
        except AttributeError as exc:
            import_exception = exc
        except ImportError as exc:
            import_exception = exc
        if logger:
            logger.info("Unable to load %s as a local module, exception: %s", module_name, import_exception)
        return None

    @staticmethod
    def direct_import(module_name, name, directory_path, logger=None):
        """
        Import a file by name (without extension) from some path.
        Then register it as a certain module name.

        For example:

        "foo.bar", "bar", "/home/user/foo/"

        Imports ``foo.bar`` from the file "/home/user/foo/bar.py"*.

        * Next to .py, this can also be .pyc or dynamic library

        :param module_name: the fully qualified module path
        :param name: the (extensionless) file name
        :param directory_path: the file's path
        :return: the imported module or None
        """
        if module_name in sys.modules and sys.modules[module_name]:
            return sys.modules[module_name]
        module = None
        f = None
        try:
            f, pathname, desc = imp.find_module(name, [directory_path, ])
            module = imp.load_module(module_name, f, pathname, desc)
        except ImportError as e:
            if logger:
                logger.error("Unable to import %s from %s as %s: %s", name, directory_path, module_name, str(e))
        finally:
            if f:
                f.close()
        return module

    @staticmethod
    def find_modules_for(directory_path):
        """
        Every folder with an __init__ should be loaded for a path.
        This allows the file to normally perform imports.

        For example in the structure:

        /
        /foo/__init.py
        /foo/bar/__init__.py
        /foo/bar/myclass.py

        find_modules("foo.bar.myclass.MyClass.SubClass")
         > [("foo", "/foo"), ("foo.bar", "/foo/bar")],
         > ("myclass", "/foo/bar"),
         > ["MyClass", "SubClass"]

        Note that the top folder does not contain an init and is not returned

        :param directory_path: the user specified module name
        :return: a list of tuples of module name and folder, target file, remaining classes
        """
        # Parse input as a list of folders | file | classes
        folder_list = directory_path.split('.')

        # Setup the root folder and root name
        current_folder = os.path.dirname(os.path.dirname(__file__))
        module_tree = ""

        # Containers for output
        out = [] # List of tuples
        out_file = "" # File name containing actual module

        # Traverse the file structure
        folder_index = 0
        for folder in folder_list:
            folder_index += 1
            candidate = os.path.join(current_folder, folder)
            # If this folder contains an __init__, add it to the output
            if os.path.isfile(os.path.join(current_folder, "__init__.py")) or \
                    os.path.isfile(os.path.join(current_folder, "__init__.pyc")):
                out.append((module_tree, current_folder))
            # If this is a directory, step into it
            # Otherwise, we have found our file
            if os.path.isdir(candidate):
                module_tree = '.'.join([module_tree, folder]) if module_tree else folder
                current_folder = candidate
            else:
                out_file = folder
                break

        out_file_module = '.'.join([module_tree, out_file]) if module_tree else out_file

        return out, (out_file_module, out_file, current_folder), folder_list[folder_index:]

    @staticmethod
    def perform_class_import(logger, line_number, directory_path):
        """
        Import a user specified class from a fully qualified path.

        :param logger: the logger to use
        :param line_number: the source line
        :param directory_path: the fully qualified path
        :return: the imported class or None
        """
        init_folders, (file_module, file_name, file_dir), classes = ExperimentClient.find_modules_for(directory_path)

        # Attempt a local import
        stuff = ExperimentClient.local_import(file_module, logger)

        if not stuff:
            # Local import failed, fall back to non-local import
            # Mimic the parent modules
            for mod, folder in init_folders:
                ExperimentClient.direct_import(mod, "", folder, logger)
            # Load the actual module
            stuff = ExperimentClient.direct_import(file_module, file_name, file_dir, logger)

        if not stuff:
            # Both local and non-local imports failed
            logger.error("Unable to import %s (from %s:%d)", directory_path, file_name, line_number, exc_info=True)
            return None

        return reduce(getattr, classes, stuff)

    def _preproc_module(self, filename, line_number, line):
        """
        Handler for preprocessor directive 'module'. It invokes the python import built-in to find the module.

        Without a fully qualified name:

        &module trustchain_module
        Will attempt to find trustchain_module.py on the python path and import it. (The python path should be set by
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
        stuff = self.perform_class_import(self._logger, line_number, line)

        # If something has not been loaded previously.
        if stuff not in self.loaded_experiment_module_classes:
            self.loaded_experiment_module_classes.append(stuff)
            self._logger.info("Loaded module: %s", line)
            if hasattr(stuff, "on_module_load") and callable(stuff.on_module_load):
                stuff.on_module_load(self)
