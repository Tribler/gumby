import random
from os import environ, path

from configobj import ConfigObj

from validate import Validator

conf_spec = '''
experiment_name = string
workspace_dir = string(default="./")
output_dir = string(default="output")

experiment_server_cmd = string(default="")

local_setup_cmd = string(default="")

local_instance_cmd = string(default="")

post_process_cmd = string(default="")

use_local_venv = boolean(default=True)
virtualenv_dir = string(default="$HOME/venv")
'''


def loadConfig(file_path):
    spec = conf_spec.splitlines()
    config = ConfigObj(file_path, configspec=spec)
    validator = Validator()
    config.validate(validator)
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
