#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import os
import sys
import time
import json

from km.fm.port import Port
from km.fm.node import Node
from km.fm.log  import Log

# ----------------------------------------------------------------------------------------------------------------------

class Switch(Node):

    def __init__(self, name, profile):
        #
        # The Node super-class will load the attributes and the chassis.
        #
        super().__init__(name, profile)

        port_start = 0
        ports_per_switch = len(profile['ports'])//2

        #
        # Get the port attribute names.
        #
        port_attr_names = []

        switches_attr = self.configuration['/redfish/v1/Fabrics/GenZ/Switches']

        for switch_index, switch_member in enumerate(switches_attr['Members']):
            switch_attr_name = switch_member['@odata.id']
            switch_attr = self.configuration[switch_attr_name]

            ports_attr_name = switch_attr['Ports']['@odata.id']
            ports_members = self.configuration[ports_attr_name]['Members']

            port_attr_names.extend([ entry['@odata.id'] for entry in ports_members ])

        #
        # Create the ports from the port attribute names.
        #
        self.create_ports(port_attr_names)


    def load_specific(self, args, kwargs):
        #
        # Load switch specific attributes.
        #
        return True

# ----------------------------------------------------------------------------------------------------------------------
