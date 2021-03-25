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

from km.fm.port     import Port
from km.fm.node     import Node
from km.fm.log      import Log
from km.fm.pidt     import PIDT
from km.fm.rit      import RIT
from km.fm.vcat     import REQ_VCAT
from km.fm.vcat     import RSP_VCAT
from km.fm.routeset import LPRT
from km.fm.routeset import MPRT
from km.fm.routeset import SSDT
from km.fm.routeset import MSDT

# ----------------------------------------------------------------------------------------------------------------------

class IO(Node):

    def __init__(self, name, profile):
        #
        # The Node super-class will load the attributes and the chassis.
        #
        super().__init__(name, profile)

        #
        # Get the system.
        #
        system_attr_name = self.configuration['/redfish/v1/Systems']['Members'][0]['@odata.id']
        fabric_adapters_name = self.configuration[system_attr_name]['FabricAdapters']['@odata.id']

        fabric_adapters = self.configuration[fabric_adapters_name]
        for fabric_adapter_entry in fabric_adapters['Members']:
            fabric_adapter_name = fabric_adapter_entry['@odata.id']
            fabric_adapter = self.configuration[fabric_adapter_name]
            genz_attributes = fabric_adapter.get('Gen-Z', None)

            if genz_attributes:
                if 'SSDT' in genz_attributes: self.ssdt = SSDT(self, genz_attributes['SSDT']['@odata.id'])
                if 'MSDT' in genz_attributes: self.msdt = MSDT(self, genz_attributes['MSDT']['@odata.id'])

                if 'REQ-VCAT' in genz_attributes: self.req_vcat = REQ_VCAT(self, genz_attributes['REQ-VCAT']['@odata.id'])
                if 'RSP-VCAT' in genz_attributes: self.rsp_vcat = RSP_VCAT(self, genz_attributes['RSP-VCAT']['@odata.id'])

                if 'RIT'  in genz_attributes: self.rit  = RIT(self, fabric_adapter_name)
                if 'PIDT' in genz_attributes: self.pidt = PIDT(self, fabric_adapter_name)

        #
        # We don't have an LPRT or MPRT here.
        #
        self.lprt = None
        self.mprt = None

        #
        # Setup the system fabric adapter ports.
        #
        port_attr_names = None
        if 'Ports' in fabric_adapter:
            fabric_adapter_ports_attr_name = fabric_adapter['Ports']['@odata.id']
            fabric_adapter_ports_attr = self.configuration[fabric_adapter_ports_attr_name]
            fabric_adapter_ports_members = fabric_adapter_ports_attr['Members']

            port_attr_names = [ entry['@odata.id'] for entry in fabric_adapter_ports_members ]

        #
        # Create the ports from the port attribute names.
        #
        self.create_ports(port_attr_names)


    def load_specific(self, args, kwargs):
        status = True

        #
        # Load io specific attributes.
        #
        status &= self.req_vcat.patch()
        status &= self.rsp_vcat.patch()

        status &= self.ssdt.patch()
        status &= self.msdt.patch()

        status &= self.pidt.patch()
        status &= self.rit.patch()

        return status

# ----------------------------------------------------------------------------------------------------------------------

