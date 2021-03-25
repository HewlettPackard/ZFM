#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import os
import re
import sys
import json
import pprint
import pkgutil

from importlib import import_module


class Router():

    def __init__(self, fabric, tc_name, tc_info):
        self.tc_name = tc_name
        self.tc_info = tc_info
        self.vc_map = []
        self.name = tc_info['Parameters']['Algorithm']

        #
        # Setup the VC mappings.
        #
        tc = int(tc_name[2:])
        for pc_name in sorted(tc_info.keys()):
            if re.match(r'^PC\d+$', pc_name):
                pc_info = tc_info[pc_name]
                pc = int(pc_name[2:])

                for rc_name, rc_info in pc_info.items():
                    if re.match(r'^RC\d+$', rc_name):
                        rc = int(rc_name[2:])

                        for vc_name in rc_info:
                            vc = int(vc_name[2:])
                            self.vc_map.append((tc,pc,rc,vc))

        #
        # Load the routing class.
        #
        if True:
            algorithm = self.name
            module_name = 'km.routers.{}'.format(algorithm)
            re_module = import_module(module_name)
            class_name = algorithm[:1].upper() + algorithm[1:]
            re_class = getattr(re_module, class_name)
        else: # except ModuleNotFoundError:
            print('{} is not a known router.'.format(algorithm))
            sys.exit(1)

        self.routing_engine = re_class(fabric, tc_info['Parameters'], self.vc_map)

# ----------------------------------------------------------------------------------------------------------------------

    def get_node_vcat(self, node_name):
        return self.routing_engine.get_node_vcat(node_name)


    def get_node_routes(self, fabric, node_name):
        return self.routing_engine.get_node_routes(fabric, node_name)

# ----------------------------------------------------------------------------------------------------------------------

    def get_switch_vcat(self, switch_name):
        return self.routing_engine.get_switch_vcat(switch_name)


    def get_switch_routes(self, fabric, switch_name):
        return self.routing_engine.get_switch_routes(fabric, switch_name)

# ----------------------------------------------------------------------------------------------------------------------

    def get_action(self, route_type):
        return self.routing_engine.get_action(route_type)


    def get_hopcount(self, route_type):
        return self.routing_engine.get_hopcount(route_type)


    def get_threshold(self, port_type, route_type, rc):
        return self.routing_engine.get_threshold(port_type, route_type, rc)

# ----------------------------------------------------------------------------------------------------------------------

    def get_switch_to_switch_routes(self, fabric, src_name, dst_name):
        return self.routing_engine.get_switch_to_switch_routes(fabric, src_name, dst_name)


    def get_routing_state(self, location, port_type, exit_allowed=False):
        for loc_port,route_actions in self.routing_engine.state_machine.items():
            if loc_port == (location, port_type):
                for action in route_actions:
                    if action != 'EXIT' or exit_allowed:
                        yield action

# ----------------------------------------------------------------------------------------------------------------------
