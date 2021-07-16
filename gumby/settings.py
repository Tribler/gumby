import random
from os import environ, path

from configobj import ConfigObj

from validate import Validator

conf_spec = '''
experiment_name = string
workspace_dir = string(default="./")
remote_workspace_dir = string(default="./")
output_dir = string(default="output")
head_nodes = list(default=[])

experiment_server_run_remote = boolean(default=False)
experiment_server_cmd = string(default="")

local_setup_cmd = string(default="")
remote_setup_cmd = string(default="das4_setup.sh")

local_instance_cmd = string(default="")
remote_instance_cmd = string(default="")

post_process_cmd = string(default="")

use_local_venv = boolean(default=True)
use_remote_venv = boolean(default=True)
virtualenv_dir = string(default="$HOME/venv")
'''


def loadConfig(file_path):
    spec = conf_spec.splitlines()
    config = ConfigObj(file_path, configspec=spec)
    validator = Validator()
    config.validate(validator)
    # TODO: Find a better way to do this (If the default value for a list is an empty list, it just doesn't set the value at all)
    if 'head_nodes' not in config:
        config["head_nodes"] = []
    for key, value in config.items():
        # If any config option has the special value __unique_port__, compute a unique port for it by hashing the user
        # ID, the experiment name, the experiment execution dir and the config option name.
        if value == '__unique_port__':
            config[key] = random.randint(1000, 60000)

    # Override config options with env. variables.
    revalidate = False
    for key, value in environ.items():
        if key.startswith("GUMBY_"):
            name = key[6:].lower()  # "GUMBY_".len()
            config[name] = value
            revalidate = True
    if revalidate:
        config.validate(validator)
    config.write()
    return config


def configToEnv(config):
    """
    Processes a dictionary of config options so it can be exported as env. variables when running a subprocess.
    """
    env = {}
    for name, val in config.items():
        env[name.upper()] = path.expanduser(path.expandvars(str(val)))
    return env
