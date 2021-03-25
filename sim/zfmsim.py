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
import argparse

from threading import Thread
from km.sim.server import NodeMP

# ----------------------------------------------------------------------------------------------------------------------

def zfm_load_configuration(config_file):

    configuration = {}

    #
    # Read the file line by line.  Strip out the comments and then split the line into key and value.
    #
    with open(config_file) as f:
        for line in f:
            kv_line, _, comment = line.partition('#')
            kv_line = kv_line.strip()
            try:
                key, value = kv_line.split()
                configuration[key] = value
            except:
                print('invalid line: {}'.format(kv_line))

    return configuration

# ----------------------------------------------------------------------------------------------------------------------

def find_node_by_uid(fabric, uid):
    for name,node in fabric.items():
            if node['UID'] == uid:
                return node

    return None

# ----------------------------------------------------------------------------------------------------------------------

def main(zfm_config_file, browser):
    fabric_config_file = None
    node_config_dir = None

    #
    # Get the fabric config file name and the node config directory names.
    #
    zfm_configuration   = zfm_load_configuration(zfm_config_file)
    switch_config_file  = zfm_configuration['zfm_switch_node_file']
    compute_config_file = zfm_configuration['zfm_compute_node_file']
    memory_config_file  = zfm_configuration['zfm_memory_node_file']
    io_config_file      = zfm_configuration['zfm_io_node_file']

    #
    # Read the node profile files.
    #
    fabric = {}
    for filename in [switch_config_file, compute_config_file, memory_config_file, io_config_file]:
        with open(filename) as f:
            node_profiles = json.load(f)
            for name, profile in node_profiles.items():
                fabric[name] = profile

    #
    # Read the node configuration files.
    #
    nodes = []
    for name, profile in fabric.items():
        profile['browser'] = browser
        nodes.append(NodeMP(profile))

    #
    # Start the nodes.
    #
    threads = []

    for node in nodes:
        t = Thread(target=node.run, daemon=True)
        threads.append(t)

    for t in threads:
        t.start()

    #
    # Wait around for the nodes to exit or the user to kill us.
    #
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        return 1
    else:
        return 0

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    #
    # Get the command line parameters.
    #
    parser = argparse.ArgumentParser(description='fabric simulator')

    parser.add_argument('-d', '--dir',     help='simulated ZFM config file', required=True)
    parser.add_argument('-b', '--browser', help='href links for browsers',   required=False,  default=False,      action='store_true')

    args = vars(parser.parse_args())

    #
    # Chdir to the config directory.
    #
    try:
        os.chdir(args['dir'])
    except:
        print('{} is not accessible'.format(args['dir']))
        sys.exit(1)

    args['conf'] = 'zfm.conf'
    main(args['conf'], args['browser'])
