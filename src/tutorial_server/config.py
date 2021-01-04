import logging.config
import os

from configparser import ConfigParser
from tornado.options import options


DEFAULT_CONFIG = {
    'app': {
        'here': os.getcwd(),
    },
    'server': {
        'host': '0.0.0.0',
    },
}

config = ConfigParser()
config.read_dict(DEFAULT_CONFIG)


def setup_config():
    config.read([options.config])
    logging.config.fileConfig(config, disable_existing_loggers=False)
