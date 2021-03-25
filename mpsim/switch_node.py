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

from node import Node

# ----------------------------------------------------------------------------------------------------------------------

class Switch(Node):

    def __init__(self, data, browser):
        self.constants = data['constants']['Switch']

        switch_range = self.constants['SWITCHES']
        port_range   = self.constants['SWITCH_PORTS']

        self.num_ports = (switch_range[1] - switch_range[0] + 1) * (port_range[1] - port_range[0] + 1)
        self.ports = [ None for i in range(self.num_ports) ]

        self.port_format  = r'/redfish/v1/Fabrics/GenZ/Switches/Switch{}/Ports/{}'
        self.port_pattern = r'^/redfish/v1/Fabrics/GenZ/Switches/Switch\d+/Ports/\d+$'

        super().__init__(data, browser)


    def path_to_port(self, path):
        if re.match(self.port_pattern, path):
            tokens = path.split('/')
            switch_number = int(tokens[-3][6:])
            port_number = int(tokens[-1])

            return (self.num_ports//2)*(switch_number-1) + port_number
        else:
            return -1


    def port_to_path(self, port):
        if port < self.num_ports:
            switch_number = 1 if port < self.num_ports//2 else 2
            port_number = port if switch_number == 1 else port - self.num_ports//2
            return self.port_format.format(switch_number, port_number)
        else:
            return None

# ----------------------------------------------------------------------------------------------------------------------
