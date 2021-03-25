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
import time

from km.sim.node import Node

Switch_port_format  = r'/redfish/v1/Fabrics/GenZ/Switches/Switch{}/Ports/{}'
Switch_port_pattern = r'^/redfish/v1/Fabrics/GenZ/Switches/Switch\d+/Ports/\d+$'

# ----------------------------------------------------------------------------------------------------------------------

class Switch(Node):

    def __init__(self, server):
        super().__init__(server)


    def path_to_port(self, path):
        num_ports = len(self.port_range)

        if re.match(Switch_port_pattern, path):
            tokens = path.split('/')
            switch_number = int(tokens[-3][6:])
            port_number = int(tokens[-1])

            return (num_ports//2)*(switch_number-1) + port_number
        else:
            return -1


    def port_to_path(self, port):
        num_ports = len(self.port_range)

        if port in self.port_range:
            switch_number = 1 if port < num_ports//2 else 2
            port_number = port if switch_number == 1 else port - num_ports//2
            return Switch_port_format.format(switch_number, port_number)
        else:
            return None


    def trigger(self, base_name, data):
        if re.match(Switch_port_pattern, base_name):
            self.port_trigger(base_name, data)

# ----------------------------------------------------------------------------------------------------------------------
