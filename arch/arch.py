#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import os
import re
import sys
import copy
import json
import pprint

from importlib import import_module

PRETTY_PRINT_WIDTH = 220

# ======================================================================================================================

class Architecture():

    def __init__(self, configuration):
        self.config = configuration
        self.arch_config = configuration['Architecture']
        self.routing_config = configuration['Routing']
        self.arch_type = self.arch_config['Type']
        self.pp = pprint.PrettyPrinter(indent=4, width=PRETTY_PRINT_WIDTH, compact=True)

        #
        # Load the architecture class.
        #
        try:
            module_name = 'km.arch.{}'.format(self.arch_type)
            re_module = import_module(module_name)
            class_name = self.arch_type[:1].upper() + self.arch_type[1:]
            re_class = getattr(re_module, class_name)
        except ModuleNotFoundError:
            print('{} is not a known architecture.'.format(self.arch_type))
            sys.exit(1)

        self.arch_engine = re_class(self.arch_config['Parameters'])


    def process(self):
        nodes, connections = self.load_config()
        return self.arch_engine.process(nodes, connections, self.routing_config)


    def dump(self, file):
        self.arch_engine.dump(file)

    # ----------------------------------------------------------------------------------------------------------------------

    def load_config(self):
        nodes = self.config['Nodes']
        connections = self.config['Connections']
        constants = self.config['Constants']

        arch_nodes = []
        arch_connections = []

        #
        # Load all of the nodes.
        #
        global_constants = constants['Fabric']
        for model in nodes:
            model_constants = copy.deepcopy(constants[model])
            model_constants.update(global_constants)

            for name, profile in nodes[model].items():
                _, topoid, geoid, enabled, gcids = profile

                if enabled:
                    arch_nodes.append((name, model, topoid, geoid, gcids, model_constants))

        #
        # Add in the connections.
        #
        for src_endpoint,dst_endpoint in connections.items():
            try:
                src_name,src_port = src_endpoint.split(',')
                src_port = int(src_port)

                dst_name,dst_port = dst_endpoint.split(',')
                dst_port = int(dst_port)
            except Exception as e:
                print('bad connection : "{} : {}"'.format(src_endpoint, dst_endpoint, e))
                sys.exit(0)

            arch_connections.append((src_name, src_port, dst_name, dst_port))

        return arch_nodes, arch_connections

# ----------------------------------------------------------------------------------------------------------------------
