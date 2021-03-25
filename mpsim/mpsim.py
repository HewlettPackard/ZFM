#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import os
import sys
import json
import glob
import time
import socket
import argparse

from resolve       import resolve
from switch_node   import Switch
from compute_node  import Compute
from io_node       import IO
from memory_node   import Memory
from log           import Log

node = None
parameters = {}

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    #
    # Read the simulation parameters.
    #
    with open('/opt/km_variables') as f:
        for line in f:
            name,delimiter,value = line.rstrip().partition('=')
            parameters[name] = value

    #
    # Read the profile and attributes.
    #
    home_dir = os.path.expanduser('~')
    data_file = os.path.join(home_dir, parameters['SCENARIO'], 'profile')
    with open(data_file) as f:
        data = json.load(f)

    #
    # Start up the firmware.
    #
    browser = parameters.get('BROWSER', True)

    if parameters['NODETYPE'] == 'Switch'  : node = Switch(data, browser)
    if parameters['NODETYPE'] == 'Compute' : node = Compute(data, browser)
    if parameters['NODETYPE'] == 'IO'      : node = IO(data, browser)
    if parameters['NODETYPE'] == 'Memory'  : node = Memory(data, browser)

    #
    # Start up the logging endpoint.
    #
    Log.Init(parameters)
    Log.info('mpsim started')

    #
    # Idle while the redfish server does the work.
    #
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        Log.info('user interrupt caught - exiting')
    else:
        Log.info('Unexpected error:', sys.exc_info()[0])

# ----------------------------------------------------------------------------------------------------------------------

