#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import os
import sys
import json
import copy
import pprint


# ----------------------------------------------------------------------------------------------------------------------

class Node():

    def __init__(self, zfm_dir, node_type, node_name, node_profile, type_constants, routing_data):

        #
        # Determine the number of ports.
        #
        if node_type == 'Switch':
            uid_type = 1
            switch_range = type_constants['SWITCHES']
            port_range = type_constants['SWITCH_PORTS']
        elif node_type == 'Compute':
            uid_type = 2
            switch_range = [0, 0]
            port_range = type_constants['FABRIC_ADAPTER_PORTS']
        elif node_type == 'IO':
            uid_type = 3
            switch_range = [0, 0]
            port_range = type_constants['FABRIC_ADAPTER_PORTS']
        elif node_type == 'Memory':
            uid_type = 4
            switch_range = [0, 0]
            port_range = type_constants['SWITCH_PORTS']

        num_ports = (1 + switch_range[1] - switch_range[0]) * (1 + port_range[1] - port_range[0])
        port_start = port_range[0]
        port_end = port_start + num_ports

        #
        # Node specific values.
        #
        ip_string, topoid, geoid_string, enabled, gcids = node_profile
        geoid = geoid_string.split('.')
        if ':' not in ip_string:
            ip_string += ':8081'

        #
        # Derived values.
        #
        uid = (uid_type << 28) | int('0x{}'.format(topoid.replace('.', '')), 0)

        #
        # Point to the correct directory for my attributes and create it (if needed).
        #
        if   node_type == 'Switch': dir_name = 'switch_nodes'
        elif node_type == 'Compute': dir_name = 'compute_nodes'
        elif node_type == 'IO': dir_name = 'io_nodes'
        elif node_type == 'Memory'   : dir_name = 'memory_nodes'

        self.dir = os.path.join(zfm_dir, dir_name)

        try:
            os.makedirs(self.dir, exist_ok=True)
        except:
            print('can\'t create attribute directory for {} nodes'.format(node_type))
            sys.exit(1)

        #
        # Port configuration.  Some of the nodes have port ranges which don't start at 0.
        #
        ports = []
        for i in range(port_start):
            ports.append({ 'State' : 'Notused' })

        for i in range(port_start,port_end):
            ports.append({ 'State' : 'Disabled' })

        #
        # The actual node.
        #
        self.routing_data = routing_data

        self.config = {
            'name'       : node_name,
            'type'       : node_type,
            'hostname'   : ip_string,
            'FQDN'       : ip_string,
            'address'    : ip_string,
            'UID'        : uid,
            'TopoID'     : topoid,
            'GeoID'      : { 'RackID': geoid[0], 'ChassisID' : geoid[1], 'SlotID' : geoid[2], 'NodeID' : geoid[3] },
            'AsicID'     : { 'ComponentID' : 1 },
            'Active'     : 'Enabled' if enabled else 'Disabled',
            'GCIDs'      : list(int(gcid,0) for gcid in gcids),
            'attributes' : os.path.join(self.dir, '{}.json'.format(node_name)),
            'portStart'  : port_start,
            'portEnd'    : port_end,
            'ports'      : ports,
        }


    def configuration(self):
        return self.config


    def name(self):
        return self.config['name']


    def node_type(self):
        return self.config['type']


    def GCIDs(self):
        return self.config['GCIDs']


    def UID(self):
        return self.config['UID']


    def isActive(self):
        return self.config['Active'] == 'Enabled'


    def setRemote(self, port, dst_node, dst_port):
        self.config['ports'][port]['State'] = 'Enabled'
        self.config['ports'][port]['Remote'] = { 'Node': dst_node.name(),
						 'Port': dst_port,
						 'UID': dst_node.UID() }


    def profile(self):
        return self.config


    def write(self):

        #
        # Loop over the attributes and collect them for writing to the config file.
        #
        node_data = {}
        for attribute_name, attribute_data in self.attributes.items():
            attribute_name = attribute_name.replace('.', '/')
            node_data[attribute_name] = attribute_data

        #
        # Write the data to this nodes config file.
        #
        try:
            with open(self.config['attributes'], 'w') as f:
                json.dump(node_data,f,indent=4, separators=(",", ": "))
        except:
            print('can\'t write attribute data for node {}'.format(self.config['node_name']))
            sys.exit(1)

# ----------------------------------------------------------------------------------------------------------------------

    def create_attributes(self, type_attributes):
        attributes = copy.deepcopy(type_attributes)

        #
        # Create the Location data.
        #
        if '/redfish.v1.Chassis.1' in attributes:
            chassis = attributes['/redfish.v1.Chassis.1']
            oem_location = chassis.get('Oem', {}).get('Hpe', {}).get('Location', None)
            if oem_location is not None:
                chassis['Oem']['Hpe']['Location'] = self.config['GeoID']

        return attributes

# ----------------------------------------------------------------------------------------------------------------------

    def get(self, tokens):
        x = self.routing_data
        for a in tokens:
            x = x.get(a, {})

        return x


    def update_route_set(self, attr_name, attr_data, tokens):
        entry = self.get(tokens)
        if entry:
            for key,value in entry.items():
                attr_data[key] = value


    def update_vcat(self, attr_name, attr_data, tokens):
        entry = self.get(tokens)
        if entry:
            for key in sorted(entry.keys(), key=int):
                value = entry[key]
                attr_data['VCATEntry'].append({ 'TH' : value['Threshold'], 'VCMask' : value['VCMask'] })


    def update_Switch_routing(self):

        for attr_name,attr_data in self.attributes.items():
            #
            # redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.LPRT.{CIDS}.RouteSet.{VCS}
            # redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.MPRT.{CIDS}.RouteSet.{VCS}
            #
            m = re.match(r'.*Switch(\d+).Ports.(\d+).(LPRT|MPRT).(\d+).RouteSet.(\d+)$', attr_name)
            if m:
                p = str(60*(int(m.group(1))-1) + int(m.group(2)))
                self.update_route_set(attr_name, attr_data, ['Ports', p, m.group(3), m.group(4), 'Entries', m.group(5)])

            #
            # redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.VCAT.{VCS}
            #
            m = re.match(r'.*Switch(\d+).Ports.(\d+).VCAT.(\d+)$', attr_name)
            if m:
                p = str(60*(int(m.group(1))-1) + int(m.group(2)))
                self.update_vcat(attr_name, attr_data, ['Ports', p, 'VCAT', m.group(3)])


    def update_Compute_routing(self):

        for attr_name,attr_data in self.attributes.items():
            #
            # redfish.v1.Systems.1.FabricAdapters.{FABRIC_ADAPTERS}.Ports.{FABRIC_ADAPTER_PORTS}.LPRT.{CIDS}.RouteSet.{VCS}
            # redfish.v1.Systems.1.FabricAdapters.{FABRIC_ADAPTERS}.Ports.{FABRIC_ADAPTER_PORTS}.MPRT.{CIDS}.RouteSet.{VCS}
            #
            m = re.match(r'.*FabricAdapters.(\d+).Ports.(\d+).(LPRT|MPRT).(\d+).RouteSet.(\d+)$', attr_name)
            if m:
                p = str(60*(int(m.group(1))-1) + int(m.group(2)))
                self.update_route_set(attr_name, attr_data, ['Ports', p, m.group(3), m.group(4), 'Entries', m.group(5)])

            #
            # redfish.v1.Systems.1.FabricAdapters.{FABRIC_ADAPTERS}.Ports.{FABRIC_ADAPTER_PORTS}.VCAT.{VCS}
            #
            m = re.match(r'FabricAdapters.(\d+).Ports.(\d+).VCAT.(\d+)$', attr_name)
            if m:
                self.update_vcat(attr_name, attr_data, ['Ports', m.group(2), 'VCAT', m.group(3)])

            #
            # redfish.v1.Systems.1.FabricAdapters.{FABRIC_ADAPTERS}.SSDT.{CIDS}.RouteSet.{VCS}
            # redfish.v1.Systems.1.FabricAdapters.{FABRIC_ADAPTERS}.MSDT.{CIDS}.RouteSet.{VCS}
            #
            m = re.match(r'.*FabricAdapters.(\d+).(SSDT|MSDT).(\d+).RouteSet.(\d+)$', attr_name)
            if m:
                self.update_route_set(attr_name, attr_data, [m.group(2), m.group(3), 'Entries', m.group(4)])

            #
            # redfish.v1.Systems.1.FabricAdapters.{FABRIC_ADAPTERS}.REQ-VCAT.{VCS}
            # redfish.v1.Systems.1.FabricAdapters.{FABRIC_ADAPTERS}.RSP-VCAT.{VCS}
            #
            m = re.match(r'.*FabricAdapters.(\d+).(REQ-VCAT|RSP-VCAT).(\d+)$', attr_name)
            if m:
                self.update_vcat(attr_name, attr_data, [m.group(2), m.group(3)])


    def update_IO_routing(self):
        self.update_Compute_routing()


    def update_Memory_routing(self):
        self.update_Switch_routing()


    def update_routing(self):
        if self.node_type() == 'Switch'   : self.update_Switch_routing()
        if self.node_type() == 'Compute'  : self.update_Compute_routing()
        if self.node_type() == 'IO'       : self.update_IO_routing()
        if self.node_type() == 'Memory'   : self.update_Memory_routing()

# ----------------------------------------------------------------------------------------------------------------------

