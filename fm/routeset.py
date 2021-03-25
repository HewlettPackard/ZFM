#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import os
import sys
import json

# ----------------------------------------------------------------------------------------------------------------------

class _RouteSet():

    def __init__(self, node, name):
        self.node = node
        self.name = name
        self.configuration = self.node.configuration[name]


    def get(self):
        status,table = self.node.get(self.name)
        return status,table


    def patch(self):
        all_status = True
        for member_id in self.configuration['Members']:
            member_name = member_id['@odata.id']
            member_attr = self.node.configuration[member_name]

            route_set_name = member_attr['RouteSet']['@odata.id']
            route_set_attr = self.node.configuration[route_set_name]
            for route_set_id in route_set_attr['Members']:
                route_set_entry_name = route_set_id['@odata.id']
                route_set_entry = self.node.configuration[route_set_entry_name]
                route_set_entry_data = { id : route_set_entry[id] for id in ['Valid', 'VCAction', 'HopCount', 'EgressIdentifier'] }

                status,_ = self.node.patch(route_set_entry_name, route_set_entry_data)
                all_status &= status

        return all_status


# ----------------------------------------------------------------------------------------------------------------------

class LPRT(_RouteSet):
    def __init__(self, node, name):
        super().__init__(node, name)

# ----------------------------------------------------------------------------------------------------------------------

class MPRT(_RouteSet):
    def __init__(self, node, name):
        super().__init__(node, name)

# ----------------------------------------------------------------------------------------------------------------------

class SSDT(_RouteSet):
    def __init__(self, node, name):
        super().__init__(node, name)

# ----------------------------------------------------------------------------------------------------------------------

class MSDT(_RouteSet):
    def __init__(self, node, name):
        super().__init__(node, name)

# ----------------------------------------------------------------------------------------------------------------------
