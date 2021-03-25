#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import os
import sys
import json
import glob
import copy

from km.sim.node import Node

Memory_switch_port_format  = r'/redfish/v1/Fabrics/GenZ/Switches/Switch1/Ports/{}'
Memory_switch_port_pattern = r'^/redfish/v1/Fabrics/GenZ/Switches/Switch1/Ports/\d+$'

# ----------------------------------------------------------------------------------------------------------------------

class Memory(Node):

    def __init__(self, server):
        super().__init__(server)


    def path_to_port(self, path):
        if re.match(Memory_switch_port_pattern, path):
            tokens = path.split('/')
            return int(tokens[-1])
        else:
            return -1


    def port_to_path(self, port):
        return Memory_switch_port_format.format(port) if port in self.port_range else None


    def trigger(self, base_name, data):
        if re.match(Memory_switch_port_pattern, base_name):
            self.port_trigger(base_name, data)

# ----------------------------------------------------------------------------------------------------------------------
