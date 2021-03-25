#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import os
import sys
import json
import time
import datetime

from km.fm.log     import Log
from km.fm.memory  import Memory
from km.fm.io      import IO
from km.fm.compute import Compute
from km.fm.switch  import Switch

# ----------------------------------------------------------------------------------------------------------------------

class Fabric():

    #
    # Class variables.
    #
    name_classes = { 'Switch'  : Switch,
                     'Compute' : Compute,
                     'IO'      : IO,
                     'Memory'  : Memory,
    }

    sweep_types = [ 'light', 'medium', 'heavy' ]

    # ----------------------------------------------------------------------------------------------------------------------

    def __init__(self, sweep_type, timers, node_file_list):
        self.status = True
        self.sweep_type = sweep_type
        self.timers = timers
        self.node_file_list = node_file_list

    # ----------------------------------------------------------------------------------------------------------------------

    def initialize(self):

        #
        # Validate the sweep type.
        #
        if self.sweep_type not in Fabric.sweep_types:
            Log.error('invalid sweep type {}', self.sweep_type)
            return False

        #
        # Read the node profiles.
        #
        self.nodes = {}
        for filename in self.node_file_list:
            Log.info('reading {}', filename)
            try:
                with open(filename) as f:
                    node_profiles = json.load(f)
                    for name, profile in node_profiles.items():
                        node_type = profile['type']
                        self.nodes[name] = Fabric.name_classes[node_type](name, profile)
            except:
                Log.error('error reading {}', filename)
                return False

        #
        # There are 5 steps for node initialization:
        #   1) load the GCIDs and UID into the endpoints
        #   2) train the port links
        #   3) validate that all ports are wired correctly
        #   4) load the node attributes
        #   5) enable the port interfaces
        #
        status = True

        if status: status = self.init_ids()
        if status: status = self.train_ports()
        if status: status = self.validate_ports()
        if status: status = self.load_nodes()
        if status: status = self.enable_ports()

        #
        # Verify the state of all connected ports.
        #
        if status:
            status = self.verify_fabric_health()

        Log.debug('fabric initialization status = {}', status)
        return status

    # ----------------------------------------------------------------------------------------------------------------------

    def wait_status(self, statuses):
        return min(statuses)


    def wait_display(self, command, cycles, statuses):
            s = { -1 : '-', 0 : '0', 1 : '1' }
            status_str = ''.join(s[x] for x in statuses)
            Log.info('{} : cycles={:<4}  status={:<}', command, cycles, status_str)


    def wait_for(self, command, args, kwargs):
        Log.info('starting {}...', command)
        kwargs['retries'] = self.timers.get(command, self.timers['default'])
        verify_name = '{}_done'.format(command)

        #
        # Tell the node threads to start the command.
        #
        active_nodes = [node for node in self.nodes.values() if node.active]
        for node in active_nodes:
            node.enqueue(command, args, kwargs)

        #
        # Wait for all of the node threads to complete.
        #
        cycles = 0
        node_statuses = [-1]
        while (self.wait_status(node_statuses) < 0) and (cycles < self.timers[command]):
            time.sleep(1)
            cycles += 1

            node_statuses = [getattr(node, verify_name)() for node in active_nodes]
            if (cycles%60) == 0:
                self.wait_display(command, cycles, node_statuses)

        #
        # Check for node timeouts.
        #
        if self.wait_status(node_statuses) < 0:
            self.wait_display(command, cycles, node_statuses)

            for i in range(len(node_statuses)):
                if node_statuses[i] == -1:
                    Log.error('{} : {} timed out', command, active_nodes[i].name)

        #
        # Display the command status.
        #
        command_status = self.wait_status(node_statuses) == 1
        Log.info('{} done ... status = {}   cycles = {}', command, command_status, cycles)
        return command_status


    def init_ids(self):
        status = self.wait_for('init', [], {})
        if not status:
            Log.error('nodes not inited')
        return status


    def train_ports(self):
        status = self.wait_for('train', [], {})
        if not status:
            Log.error('ports not trained')
        return status


    def validate_ports(self):
        status = self.wait_for('validate', [], {})
        if not status:
            Log.error('ports not validated')
        return status


    def load_nodes(self):
        status = self.wait_for('load', [], {})
        if not status:
            Log.error('ports not loaded')
        return status


    def enable_ports(self):
        status = self.wait_for('enable', [], {})
        if not status:
            Log.error('ports not enabled')
        return status


    def sweep(self):
        status = self.wait_for('sweep', [self.sweep_type], {})
        if not status:
            Log.error('nodes not swept')
        return status

    # ----------------------------------------------------------------------------------------------------------------------

    def verify_fabric_health(self):
        error_count = 0
        for name,node in self.nodes.items():
            if not node.active: continue

            for port in node.ports:
                if port.active:
                    remote_node = self.locate_node(port.remote_uid)
                    if not remote_node:
                        Log.error('failed node connectivity test : {}/{}', name, port.index)
                        error_count += 1
                        continue

                    remote_port = remote_node.ports[port.remote_port]
                    if not remote_port:
                        Log.error('failed port connectivity test : {}/{}', name, port.index)
                        error_count += 1
                        continue

                    if remote_port.current['Status']['Health'] != 'OK':
                        Log.error('pair not healthy : {}/{} <-> {}/{}', name, port.index, remote_node.name, remote_port.index)
                        error_count += 1
                        continue

                    if remote_port.current['InterfaceState'] != 'Enabled':
                        Log.error('pair not enabled : {}/{} <-> {}/{}', name, port.index, remote_node.name, remote_port.index)
                        error_count += 1
                        continue

        if error_count > 0:
            Log.error('can\'t verify remote port state')

        return True if error_count == 0 else False

    # ----------------------------------------------------------------------------------------------------------------------

    def locate_node(self, node_id):
        node_hex_id = -1

        if type(node_id) is int:
            node_hex_id = node_id
        elif type(node_id) is str and node_id.isdigit():
            node_hex_id = int(node_id, 0)

        for name,node in self.nodes.items():
            if name == node_id:
                return node
            elif node.topoid == node_id:
                return node
            elif node.geoid == node_id:
                return node
            elif node.uid == node_hex_id:
                return node

        Log.error('invalid node identifier {}', node_id)
        return None

    # ----------------------------------------------------------------------------------------------------------------------

    def GET_fabric(self, parameters):
        data = { 'DataType'  : 'FABRIC',
                 'Timestamp' : datetime.datetime.now().isoformat(),
                 'Nodes'     : {}
        }

        for name,node in self.nodes.items():
            chassis = node.configuration.get('/redfish/v1/Chassis/1', None)

            node_type = node.profile['type']
            ip_address = node.profile['address']
            config_state = node.profile['Active']
            if config_state == 'Enabled':
                power_state = chassis['PowerState']
                status = chassis['Status']
            else:
                power_state = None
                status = None

            if 'type' not in parameters or node.type in parameters['type']:
                data['Nodes'][name] = { 'Type'       : node_type,
                                        'Address'    : ip_address,
                                        'State'      : config_state,
                                        'PowerState' : power_state,
                                        'Status'     : status }

        return 200, data

    # ----------------------------------------------------------------------------------------------------------------------

    def GET(self, parameters):
        return self.GET_fabric(parameters)

    # ----------------------------------------------------------------------------------------------------------------------
