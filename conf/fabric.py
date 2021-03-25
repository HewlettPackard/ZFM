#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import os
import sys
import json

# ----------------------------------------------------------------------------------------------------------------------

class Fabric():

    def __init__(self, zfm_dir):
        self.config_dir = zfm_dir

        #
        # Node placeholder.
        #
        self.nodes = {}
        self.gcids = set()


    def _write_type(self, data, filename):
        filename = os.path.join(self.config_dir, filename)

        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(data, f,indent=4, separators=(",", ": "))
        except:
            print(sys.exc_info())
            sys.exit(1)


    def add_node(self,name,node):
        self.nodes[name] = node
        if node.node_type() != 'Switch':
            self.gcids |= set(node.GCIDs())


    def find_node(self,name):
        return self.nodes[name]


    def write(self):

        #
        # Bundle up the nodes so that we can write them as JSON.
        #
        switch_data  = {}
        compute_data = {}
        memory_data  = {}
        io_data      = {}

        for name,node in self.nodes.items():
            node_type = node.node_type()
            if   node_type == 'Switch'  : switch_data[name]  = node.configuration()
            elif node_type == 'Compute' : compute_data[name] = node.configuration()
            elif node_type == 'IO'      : io_data[name]      = node.configuration()
            elif node_type == 'Memory'  : memory_data[name]  = node.configuration()

        #
        # Create the directories and write the profiles for the nodes.
        #
        self._write_type(switch_data,  'switch_nodes.conf')
        self._write_type(compute_data, 'compute_nodes.conf')
        self._write_type(io_data,      'io_nodes.conf')
        self._write_type(memory_data,  'memory_nodes.conf')

# ----------------------------------------------------------------------------------------------------------------------

