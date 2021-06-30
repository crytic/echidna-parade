import os.path

from collections import namedtuple
from yaml import safe_load
from os import getpid


def create_parade_config(pargs, parser):
    """
    Process the raw arguments, returning a namedtuple object holding the
    entire configuration, if everything parses correctly.
    """
    pdict = pargs.__dict__
    if pargs.name is None:
        pargs.name = "parade." + str(getpid())

    if pargs.files is None:
        parser.print_help()
        raise ValueError("You must specify some files to test!")
    # create a namedtuple object for fast attribute lookup
    key_list = list(pdict.keys())
    arg_list = [pdict[k] for k in key_list]

    Config = namedtuple("Config", key_list)
    nt_config = Config(*arg_list)
    return nt_config
