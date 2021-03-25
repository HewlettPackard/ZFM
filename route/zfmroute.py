#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#


import os
import sys
import json
import argparse

from km.arch.arch     import Architecture
from km.route.printer import Printer

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    #
    # Get the command line parameters.
    #
    parser = argparse.ArgumentParser(description='fabric router')

    parser.add_argument('-c', '--config',    help='configuration file',   required=True)
    parser.add_argument('-r', '--route',     help='route file',           required=True)
    parser.add_argument('-d', '--debug',     help='dump debug output',    required=False,  default=False, action='store_true')

    args = vars(parser.parse_args())

    config_file = args['config']
    routing_file = args['route']
    debug_flag = args['debug']

    #
    # Read the configuration.
    #
    with open(config_file) as f:
        configuration = json.load(f)

    #
    # Process the configuration.
    #
    arch = Architecture(configuration)
    routing_data = arch.process()

    #
    # Print out the results.
    #
    printer = Printer(routing_file, debug_flag)
    printer.print_data(routing_data)
