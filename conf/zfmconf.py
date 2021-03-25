#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import os
import sys
import json
import argparse

from km.conf.fabric import Fabric
from km.conf.config import Config
from km.conf.node   import Node

# ----------------------------------------------------------------------------------------------------------------------

def expand(v):
    start,end = int(v[0]), int(v[1])
    return list(range(start, end+1))

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    #
    # Get the command line parameters.
    #
    parser = argparse.ArgumentParser(description='fabric simulator')

    parser.add_argument('-c', '--config',    help='configuration file',   required=True)
    parser.add_argument('-d', '--dir',       help='ZFM config directory', required=False,  default=os.path.join(os.sep, 'opt','zfm'))
    parser.add_argument('-r', '--route',     help='routing file',         required=False,  default=None)

    args = vars(parser.parse_args())

    zfm_dir      = os.path.abspath(args['dir'])

    #
    # Make the configuration directory.
    #
    try:
        os.makedirs(zfm_dir, exist_ok=True)
    except:
        print('can\'t make ZFM directory {}'.format(zfm_dir))
        sys.exit(1)

    #
    # Read the configuration.
    #
    with open(args['config']) as f:
        fabric_configuration = json.load(f)

    nodes = fabric_configuration['Nodes']
    connections = fabric_configuration['Connections']
    constants = fabric_configuration['Constants']
    timers = constants['Timers']

    #
    # Read the routing data.
    #
    routing_data = {}
    if args['route']:
        with open(args['route']) as f:
            routing_data = json.load(f)

    #
    # Create the fabric.
    #
    fabric = Fabric(zfm_dir)

    for node_type in nodes:
        type_constants = constants[node_type]

        for name, profile in nodes[node_type].items():
            node_routing = routing_data.get(name, None)
            node = Node(zfm_dir, node_type, name, profile, type_constants, node_routing)
            fabric.add_node(name, node)

    #
    # Add in the connections.
    #
    for src_endpoint,dst_endpoint in connections.items():
        try:
            src_name,src_port = src_endpoint.split(',')
            src_node = fabric.find_node(src_name)
            src_port = int(src_port)
        except:
            print('bad src connection', src_endpoint, dst_endpoint)
            continue

        try:
            dst_name,dst_port = dst_endpoint.split(',')
            dst_node = fabric.find_node(dst_name)
            dst_port = int(dst_port)
        except:
            print('bad dst connection', src_endpoint, dst_endpoint)
            continue

        if src_node.isActive() and dst_node.isActive():
            src_node.setRemote(src_port,dst_node,dst_port)
            dst_node.setRemote(dst_port,src_node,src_port)

    #
    # Write the ZFM config file.
    #
    switch_file  = os.path.join(zfm_dir, 'switch_nodes.conf')
    compute_file = os.path.join(zfm_dir, 'compute_nodes.conf')
    memory_file  = os.path.join(zfm_dir, 'memory_nodes.conf')
    io_file      = os.path.join(zfm_dir, 'io_nodes.conf')

    zfm_config = { 'zfm_management_network'  : 'out-of-band',       # prototype is out-of-band management
                   'zfm_switch_node_file'    : switch_file,         # directory containing switch JSON configuration data
                   'zfm_compute_node_file'   : compute_file,        # directory containing compute JSON configuration data
                   'zfm_memory_node_file'    : memory_file,         # directory containing memory JSON configuration data
                   'zfm_io_node_file'        : io_file,             # directory containing IO JSON configuration data
                   'zfm_default_timer'       : timers['DEFAULT'],   # default timer for unspecified functions
                   'zfm_init_timer'          : timers['INIT'],      # seconds before timing out
                   'zfm_train_timer'         : timers['TRAIN'],     # seconds before timing out
                   'zfm_validate_timer'      : timers['VALIDATE'],  # seconds before timing out
                   'zfm_load_timer'          : timers['LOAD'],      # seconds before timing out
                   'zfm_enable_timer'        : timers['ENABLE'],    # seconds before timing out
                   'zfm_sweep_timer'         : timers['SWEEP'],     # seconds between fabric health checks
                   'zfm_HA'                  : 0,                   # HA not enabled
                   'zfm_HA_master'           : 1,                   # HA master
                   'zfm_HA_interval'         : 60,                  # HA heartbeat interval
                   'zfm_HA_count'            : 3,                   # HA count of failed heartbeats before failover
    }

    zfm_config_file = os.path.join(zfm_dir, 'zfm.conf')
    with open(zfm_config_file,'w') as f:
        for key,value in zfm_config.items():
            print('{:<30}  {:<30}'.format(key,value),file=f)

    #
    # Write the fabric config files.
    #
    fabric.write()

    #
    # Resolve the nodes.  We do this type by type so that we can preprocess some of the invariant data.
    #
    global_constants = { x : expand(v) for x,v in constants['Fabric'].items() }
    global_constants['CIDS'] = list(set(gcid & 0xfff for gcid in fabric.gcids))
    global_constants['SIDS'] = list(set(gcid >> 12   for gcid in fabric.gcids))

    node_constants = {}
    for node_type in nodes:
        node_constants = { x : expand(v) for x,v in constants[node_type].items() }
        node_constants.update(global_constants)

        Config.resolve_type(node_type, node_constants, routing_data, fabric)

    #
    # Update the actual routing data in the configured attributes.
    #
    if routing_data:
        print('updating routing')
        for name,node in fabric.nodes.items():
            print('\tprocessing', name)
            node.update_routing()

    #
    # Write the fabric node files.
    #
    print('writing config files')
    for name,node in fabric.nodes.items():
        print('\twriting', name)
        node.write()
