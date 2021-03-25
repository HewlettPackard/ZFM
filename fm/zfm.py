#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import os
import sys
import json
import time
import signal
import socket
import argparse

from threading import Thread

from km.fm.log    import Log
from km.fm.node   import Node
from km.fm.fabric import Fabric
from km.fm.server import Server

# ----------------------------------------------------------------------------------------------------------------------

def zfm_load_configuration(config_file, zfm_config):

    #
    # Open the file for reading.
    #
    try:
        f = open(config_file)
    except FileNotFound:
        Log.error('no such file: {}', config_file)
        return False

    #
    # Read the file line by line.  Strip out the comments and then split the line into key and value.
    #
    errors = False
    for line in f:
        kv_line, _, _ = line.partition('#')
        kv_line = kv_line.strip()
        if len(kv_line) == 0: continue

        tokens = kv_line.split()
        if len(tokens) == 2:
            key, value = tokens
            zfm_config[key] = value
        else:
            Log.error('invalid line: {}', line.rstrip())
            errors = True

    return not errors

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    #
    # Get the command line parameters.
    #
    parser = argparse.ArgumentParser(description='Gen-Z fabric manager')
    parser.add_argument('-d', '--dir',   help='zfm config file',  required=False,  default=os.path.join(os.sep, 'opt','zfm'))
    parser.add_argument('-H', '--host',  help='server address',   required=False,  default=socket.gethostname())
    parser.add_argument('-l', '--log',   help='log level',        required=False,  default='warning')
    parser.add_argument('-s', '--sweep', help='sweep type',       required=False,  default='light')

    args = vars(parser.parse_args())
    args['conf'] = 'zfm.conf'

    Log.Init(args['log'])

    #
    # Chdir to the config directory.
    #
    try:
        os.chdir(args['dir'])
    except:
        Log.error('{} is not accessible', args['dir'])
        sys.exit(1)

    zfm_config_file = args['conf']
    zfm_sweep_type = args['sweep']
    hostname = args['host']

    #
    # Read the ZFM configuration file.
    #
    zfm_configuration = {}
    if not zfm_load_configuration(zfm_config_file, zfm_configuration):
        Log.error('invalid ZFM config file')
        sys.exit(1)

    timers = { 'default'  : int(zfm_configuration['zfm_default_timer']),
               'init'     : int(zfm_configuration['zfm_init_timer']),
               'train'    : int(zfm_configuration['zfm_train_timer']),
               'validate' : int(zfm_configuration['zfm_validate_timer']),
               'load'     : int(zfm_configuration['zfm_load_timer']),
               'enable'   : int(zfm_configuration['zfm_enable_timer']),
               'sweep'    : int(zfm_configuration['zfm_sweep_timer']),
    }

    config_files = [ zfm_configuration['zfm_switch_node_file'],
                     zfm_configuration['zfm_compute_node_file'],
                     zfm_configuration['zfm_memory_node_file'],
                     zfm_configuration['zfm_io_node_file'],
    ]

    #
    # Create the fabric and server.
    #
    fabric = Fabric(zfm_sweep_type, timers, config_files)
    server = Server(hostname,fabric)

    #
    # Initialize the fabric.
    #
    try:
        if not fabric.initialize():
            Log.error('fabric initialization failed')
            sys.exit(1)
    except KeyboardInterrupt:
        Log.info('user interrupt caught - exiting')
        sys.exit(1)

    #
    # Start the HTTP server.
    #
    server_thread = Thread(target=server.run, daemon=True)
    server_thread.start()

    #
    # Monitor the fabric.
    #
    try:
        while True:
            fabric.sweep()
            time.sleep(timers['sweep'])
    except KeyboardInterrupt:
        Log.info('user interrupt caught - exiting')
    else:
        Log.info('Unexpected error:', sys.exc_info()[0])

