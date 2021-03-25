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
import time
import shutil
import random
import itertools

from km.templates.io_attributes      import io_attributes
from km.templates.memory_attributes  import memory_attributes
from km.templates.switch_attributes  import switch_attributes
from km.templates.compute_attributes import compute_attributes


routing_keywords = [ 'LPRT', 'MPRT', 'SSDT', 'MSDT' ]

# ----------------------------------------------------------------------------------------------------------------------

class Config():

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

    @staticmethod
    def create_members(data_json, constants, constants_range):
        if 'Members@odata.count' in data_json and type(data_json['Members@odata.count']) is str:
            count_name = data_json['Members@odata.count'][1:-1]
            saved_count = constants[count_name]
            data_json['Members@odata.count'] = len(constants_range[count_name])

            member_string = data_json['Members'][0]['@odata.id']

            data_json['Members'] = []
            for i in constants_range[count_name]:
                constants[count_name] = i
                data_json['Members'].append({ '@odata.id' : member_string.format(**constants) })

            constants[count_name] = saved_count

        return data_json

# ----------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def create_Switch_data(attribute_name, data_json, constants, constants_range):
        #
        # Switch special case - update endpoint connection.
        #
        if attribute_name.endswith('Fabrics.GenZ.Endpoints.{ENDPOINTS}'):
            component_id = data_json.get('Oem', {}).get('Hpe', {}).get('Location', {}).get('ComponentID', None)
            if component_id:
                data_json['Oem']['Hpe']['Location']['ComponentID'] = int(component_id)


    @staticmethod
    def create_Compute_data(attribute_name, data_json, constants, constants_range):
        #
        # Compute special case - endpoint has a list of Ports to link to.
        #
        if attribute_name.endswith('Fabrics.GenZ.Endpoints.{ENDPOINTS}'):
            data_json['Links'] = { 'Ports' : [0 for i in constants_range['FABRIC_ADAPTER_PORTS'] ] }
            for i in constants_range['FABRIC_ADAPTER_PORTS']:
                data_json['Links']['Ports'][i] = { '@odata.id': '/redfish/v1/Systems/1/FabricAdapters/1/Ports/{}'.format(i) }

        if attribute_name.endswith('Systems.1.FabricAdapters.{FABRIC_ADAPTERS}'):
            data_json['ControllerCapabilities']['FabricAdapterPortCount'] = len(constants_range['FABRIC_ADAPTER_PORTS'])

            data_json['Gen-Z']['RIT'] = [ { 'EIM' : 0xffff } for i in range(16) ]
            data_json['Gen-Z']['PIDT'] = [ { 'MinTimeDelay' : 1 } for i in range(32) ]


    @staticmethod
    def create_IO_data(attribute_name, data_json, constants, constants_range):
        #
        # IO mimics Compute, so we just call its function.
        #
        Config.create_Compute_data(attribute_name, data_json, constants, constants_range)


    @staticmethod
    def create_Memory_data(attribute_name, data_json, constants, constants_range):
        #
        # Memory special case - the memory node has 12 switch ports and only 6 endpoints.  Also, the last endpoint is NOT
        # connected to a media controller.
        #
        if attribute_name.endswith('Fabrics.GenZ.Switches.Switch1.Ports.{SWITCH_PORTS}'):
            if constants['SWITCH_PORTS'] >= 5:
                del data_json['Links']

        if attribute_name.endswith('Chassis.1.MediaControllers.{MEDIA_CONTROLLERS}.Ports.{MEDIA_CONTROLLER_PORTS}'):
            controller_index = constants['MEDIA_CONTROLLERS']
            tokens = data_json['Links']['ConnectedSwitchPorts'][0]['@odata.id'].split('/')
            port_number = controller_index if controller_index >= 3 else controller_index - 1
            tokens[-1] = str(port_number)
            data_json['Links']['ConnectedSwitchPorts'][0]['@odata.id'] = '/'.join(tokens)

        if attribute_name.endswith('Fabrics.GenZ.Endpoints.{ENDPOINTS}'):
            if constants['ENDPOINTS'] == 5:
                data_json['Name'] = 'RockStar Local Switch'
                data_json['Description'] = 'RockStar Control Space'

                data_json['ConnectedEntities'][0]['EntityType'] = 'Switch'
                data_json['ConnectedEntities'][0]['EntityRole'] = 'Target'
                data_json['ConnectedEntities'][0]['EntityLink'] = { '@odata.id': '/redfish/v1/Fabrics/GenZ/Switches/Switch1' }

                del data_json['ConnectedEntities'][1]
                del data_json['Links']

        if attribute_name.endswith('Chassis.1.Memory.{MEMORIES}'):
            i = constants['MEMORIES']-1
            data_json['DeviceLocator'] = 'ION {} DIMM {}'.format(1+(i//4), 1+(i%4))

        if attribute_name.endswith('Chassis.1.MemoryDomains.{MEMORY_DOMAINS}'):
            if 'InterleavableMemorySets' in data_json:
                data_json['InterleavableMemorySets'][0]['MemorySet'] = [ 0 for i in range(4) ]
                for i in range(1,4+1):
                    j = i + 4*(constants['MEMORY_DOMAINS']-1)
                    # data_json['InterleavableMemorySets'][i-1] = { '@odata.id': '/redfish/v1/Chassis/1/Memory/{}'.format(i) }
                    data_json['InterleavableMemorySets'][0]['MemorySet'][i-1] = { '@odata.id' : '/redfish/v1/Chassis/1/Memory/{}'.format(j) }

        if attribute_name.endswith('Chassis.1.MemoryDomains.{MEMORY_DOMAINS}.MemoryChunks.{MEMORY_CHUNKS}'):
            if 'InterleaveSets' in data_json:
                data_json['InterleaveSets'] = [ 0 for i in range(4) ]
                for i in range(1,4+1):
                    j = i + 4*(constants['MEMORY_DOMAINS']-1)
                    data_json['InterleaveSets'][i-1] = { 'Memory' : { '@odata.id' : '/redfish/v1/Chassis/1/Memory/{}'.format(j) }}

# ----------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def create_data(node_type, attribute_name, data_template, constants, constants_range):

        data_json = copy.deepcopy(data_template)

        #
        # Node specific special cases.
        #
        if node_type == 'IO'      : Config.create_IO_data     (attribute_name, data_json, constants, constants_range)
        if node_type == 'Memory'  : Config.create_Memory_data (attribute_name, data_json, constants, constants_range)
        if node_type == 'Switch'  : Config.create_Switch_data (attribute_name, data_json, constants, constants_range)
        if node_type == 'Compute' : Config.create_Compute_data(attribute_name, data_json, constants, constants_range)

        #
        # Create member names and resolve constants.
        #
        data_json = Config.create_members(data_json, constants, constants_range)

        #
        # Replace all occurrences of '{FIELD}' with the actual value.
        #
        data_string = json.dumps(data_json,indent=4)
        data_string = Config.resolve_constants(data_string, constants)

        return data_string

# ----------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def resolve_constants(data, constants):
        for c,v in constants.items():
            data = data.replace('{' + c + '}', str(v))

        return data

    @staticmethod
    def possible_values(constants, all_constants):
        return { x : all_constants[x] for x in constants }

# ----------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def process_regular_template(node_type, attribute_name, attribute_data, constants):
        constants_regex = '{[_A-Z0-9]+}'
        attributes = {}

        data = copy.deepcopy(attribute_data)

        #
        # Find the constants in the attribute name.
        #
        name_constants = set([ x[1:-1] for x in re.findall(constants_regex, attribute_name) ])
        name_constants_range = Config.possible_values(name_constants, constants)
        name_constants_combinations = list(itertools.product(*[value for name,value in name_constants_range.items()]))

        #
        # Find the constants in the attribute data but are NOT in the attribute name.
        #
        data_constants = set([ x[1:-1] for x in re.findall(constants_regex, data.replace('\n', '')) ])
        data_constants = data_constants - name_constants
        data_constants_range = Config.possible_values(data_constants, constants)
        data_constants_combinations = list(itertools.product(*[value for name,value in data_constants_range.items()]))

        #
        # Loop over all of the possibilities and resolve the constants.
        #
        for c in name_constants_combinations:
            d = dict(zip(name_constants, c))
            f = attribute_name.format(**d)

            instance_data = Config.resolve_constants(data, d)
            data_json = json.loads(instance_data)

            name = '/' + f
            if name not in attributes:
                if len(data_constants) == 0:
                    attributes[name] = json.loads(instance_data)
                else:
                    for x in data_constants_combinations:
                        d = dict(zip(data_constants, x))

                        data_string = Config.create_data(node_type, attribute_name, data_json, d, data_constants_range)
                        attributes[name] = json.loads(data_string)

        return attributes

# ----------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def routing_type_to_entries(node, port_number, routing_type):
        if routing_type in ['LPRT','MPRT']:
            routing_entries = node.routing_data['Ports'][str(port_number)][routing_type]
        else:
             routing_entries = node.routing_data[routing_type]

        return routing_entries


    @staticmethod
    def process_routing_template(node, node_type, attribute_name, attribute_data, constants):

        #
        # Routing parameters.
        #
        for routing_type in routing_keywords:
            if routing_type in attribute_name: break

        port_type = 'SWITCH_PORTS' if node.node_type() in ['Switch', 'Memory'] else 'FABRIC_ADAPTER_PORTS'
        id_type   = 'CIDS' if routing_type in ['LPRT', 'SSDT'] else 'SIDS'

        routing_configurations = []

        #
        # These files need to have one port number and all the cids/sids that can be reached from that port.
        #
        if re.match(r'.*(LPRT|MPRT|SSDT|MSDT)$', attribute_name):
            if routing_type in ['LPRT','MPRT']:
                for port,port_data in node.routing_data['Ports'].items():
                    p = int(port)
                    routing_table = port_data[routing_type]
                    routing_configurations.append([('SWITCHES', [str(1+p//60)]),
                                                   (port_type, [str(p%60)]),
                                                   (id_type, list(routing_table.keys()))])
            else:
                routing_table = node.routing_data[routing_type]
                routing_configurations.append([(id_type, list(routing_table.keys()))])

        #
        # These files need to have one port number and one cid/sid that can be reached from that port.
        #
        if re.match(r'.*(LPRT|MPRT|SSDT|MSDT).({CIDS}|{SIDS})$', attribute_name):
            if routing_type in ['LPRT','MPRT']:
                for port,port_data in node.routing_data['Ports'].items():
                    p = int(port)
                    routing_table = port_data[routing_type]
                    for cid_or_sid in routing_table:
                        routing_configurations.append([('SWITCHES', [str(1+p//60)]),
                                                       (port_type, [str(p%60)]),
                                                       (id_type, [ cid_or_sid ])])
            else:
                routing_table = node.routing_data[routing_type]
                for cid_or_sid in routing_table:
                    routing_configurations.append([(id_type, [ cid_or_sid ])])

        #
        # These files need to have one port number, one cid/sid and all of the routes to reach that cid/sid from the port.
        #
        if re.match(r'.*(LPRT|MPRT|SSDT|MSDT).*.RouteSet$', attribute_name):
            if routing_type in ['LPRT','MPRT']:
                for port,port_data in node.routing_data['Ports'].items():
                    p = int(port)
                    routing_table = port_data[routing_type]
                    for cid_or_sid in routing_table:
                        routing_configurations.append([('SWITCHES', [str(1+p//60)]),
                                                       (port_type, [str(p%60)]),
                                                       (id_type, [ cid_or_sid ]),
                                                       ('ROUTES', list(routing_table[cid_or_sid]['Entries'].keys()))])
            else:
                routing_table = node.routing_data[routing_type]
                for cid_or_sid in routing_table:
                    routing_configurations.append([(id_type, [ cid_or_sid ]),
                                                   ('ROUTES', list(routing_table[cid_or_sid]['Entries'].keys()))])

        #
        # These files need to have one port number, one cid/sid and one routes to reach that cid/sid from the port.
        #
        if re.match(r'.*(LPRT|MPRT|SSDT|MSDT).({CIDS}|{SIDS}).RouteSet.{ROUTES}$', attribute_name):
            if routing_type in ['LPRT','MPRT']:
                for port,port_data in node.routing_data['Ports'].items():
                    p = int(port)
                    routing_table = port_data[routing_type]
                    for cid_or_sid in routing_table:
                        for route in routing_table[cid_or_sid]['Entries']:
                            routing_configurations.append([('SWITCHES', [str(1+p//60)]),
                                                           (port_type, [str(p%60)]),
                                                           (id_type, [ cid_or_sid ]),
                                                           ('ROUTES', [ route ])])
            else:
                routing_table = node.routing_data[routing_type]
                for cid_or_sid in routing_table:
                    for route in routing_table[cid_or_sid]['Entries']:
                        routing_configurations.append([(id_type, [ cid_or_sid ]),
                                                       ('ROUTES', [ route ])])

        #
        # Process the routing configurations one at a time.
        #
        routing_attributes = {}

        for x in routing_configurations:
            for name,value in x:
                constants[name] = value

            attribute = Config.process_regular_template(node_type, attribute_name, attribute_data, constants)
            routing_attributes.update(attribute)

        return routing_attributes

# ----------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def resolve_type(node_type, constants, routing_data, fabric):
        print('preprocessing', node_type)

        if node_type == 'IO'      : node_attributes = json.loads(io_attributes)
        if node_type == 'Switch'  : node_attributes = json.loads(switch_attributes)
        if node_type == 'Memory'  : node_attributes = json.loads(memory_attributes)
        if node_type == 'Compute' : node_attributes = json.loads(compute_attributes)

        #
        # The routing files depend on the routing variables.  We save the global values so we can replace them later.
        #
        constants_copy = copy.deepcopy(constants)

        #
        # Loop over all of the attribute templates.  We will find all occurrences of variables which need to be
        # resolved.  There are 2 sets of variables we are interested in: those that appear in the attribute name
        # and those that appear in the attribute contents.  We will need to loop over all possibilities of
        # these variables in order to resolve all possible cases.
        #
        search_term = '({})'.format('|'.join(routing_keywords))
        regex = re.compile(search_term)

        regular_templates = list(node_attributes.keys())
        routing_templates = [ attribute_name for attribute_name in regular_templates if routing_data and regex.search(attribute_name) ]

        #
        # The regular files don't depend on the routing variables.  So we can do them once.
        #
        type_attributes = {}
        for attribute_name in regular_templates:
            attribute_data = json.dumps(node_attributes[attribute_name])
            type_attributes.update(Config.process_regular_template(node_type, attribute_name, attribute_data, constants))

        #
        # Process the routing files.
        #
        for name, node in fabric.nodes.items():
            if node.node_type() == node_type:
                print('\tprocessing', name)
                node.attributes = copy.deepcopy(type_attributes)

                #
                # We need specialized routing variables for these types.  Therefore we call a method which deduces
                # those variables.
                #
                for attribute_name in routing_templates:
                    attribute_data = json.dumps(node_attributes[attribute_name])
                    node.attributes.update(Config.process_routing_template(node, node_type, attribute_name, attribute_data, constants))

        #
        # Replace the original global constants.
        #
        constants = constants_copy
