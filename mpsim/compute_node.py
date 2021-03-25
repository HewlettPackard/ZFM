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

class Compute(Node):

    def __init__(self, data, browser):
        self.constants = data['constants']['Compute']

        port_range = self.constants['FABRIC_ADAPTER_PORTS']

        self.num_ports = (port_range[1] - port_range[0] + 1)
        self.ports = [ None for i in range(self.num_ports) ]

        self.port_format  = r'/redfish/v1/Systems/1/FabricAdapters/1/Ports/{}'
        self.port_pattern = r'^/redfish/v1/Systems/1/FabricAdapters/1/Ports/\d+$'

        super().__init__(data, browser)


    def path_to_port(self, path):
        if re.match(self.port_pattern, path):
            tokens = path.split('/')
            port_number = int(tokens[-1])

            return port_number
        else:
            return -1


    def port_to_path(self, port):
        return self.port_format.format(port) if 0 <= port < self.num_ports else None

# ----------------------------------------------------------------------------------------------------------------------
