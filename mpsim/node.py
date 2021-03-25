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
import shutil
import select
import socket
import random
import itertools

from threading import Thread
from server import RedfishServer
from port import Port

# ----------------------------------------------------------------------------------------------------------------------

class Node():

    def __init__(self, data, browser):
        profile = data['profile']

        #
        # Setup the environment.
        #
        self.env = data
        self.env['redfish_base'] = '/redfish/v1'
        self.env['browser'] = browser

        #
        # Create a socket endpoint for all dead-ended ports.
        #
        self.dead_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dead_address = socket.gethostbyname('127.0.0.1')
        self.dead_socket.bind((self.dead_address, Port.PORT_DEAD))

        #
        # Create the ports for IO.
        #
        self.ports = [ None for i in range(profile['portStart'], profile['portEnd']) ]

        port_info = self.env['profile']['ports']
        for src_port, dst_addr, dst_port, _, _ in self.env['remote']:
            if port_info[src_port]['State'] == 'Enabled':
                dst_uid = profile['ports'][src_port]['Remote']['UID']
                self.ports[src_port] = Port(self, 'Enabled', src_port, dst_addr, dst_port, dst_uid)

        #
        # Create the ports which are not linked.  This code will have them send packets to a dead address.
        #
        for i in range(profile['portStart'], profile['portEnd']):
            if not self.ports[i]:
                self.ports[i] = Port(self, 'Disabled', i, '127.0.0.1', -1, 0x0)

        #
        # Create the thread to run the ports.
        #
        self.thread = Thread(target=self.run, daemon=True)
        self.thread.start()

        #
        # Setup the underlying REDFish server.
        #
        self.server = RedfishServer(self)
        self.server.start()

# ----------------------------------------------------------------------------------------------------------------------

    def run(self):

        while True:
            port_sockets = [ port.socket for port in self.ports ]
            ready_sockets, _, _ = select.select(port_sockets, [], [], 1.0)
            if len(ready_sockets) > 0:
                ready_ports = [ p for p in self.ports if p.socket in ready_sockets ]
                for p in ready_ports:
                    p.process_request()
            else:
                for p in self.ports:
                    if p.state == 'Enabled':
                        p.update_port_statistics()

# ----------------------------------------------------------------------------------------------------------------------

    def update_resource(self, old_data, new_data):
        #
        # Traverse the local data struct and replace the appropriate element with new entries.
        #
        if new_data:
            for key in new_data:
                if type(old_data[key]) is dict and type(new_data[key]) is dict:
                    self.update_resource(old_data[key], new_data[key])
                else:
                    old_data[key] = copy.deepcopy(new_data[key])

# ----------------------------------------------------------------------------------------------------------------------

    #
    # REST interface functions.
    #
    def do_PATCH(self, base_name, data):
        attribute = self.env['attributes'][base_name]

        #
        # If the attribute name matches the port template, then the port will
        # process the triggering elements (if present).
        #
        if re.match(self.port_pattern, base_name):
            port_number = self.path_to_port(base_name)
            if 0 <= port_number < self.num_ports:
                port = self.ports[port_number]
                if port.is_enabled():
                    port.trigger(attribute, data)

        #
        # Update the rest of the resource.
        #
        self.update_resource(attribute, data)

# ----------------------------------------------------------------------------------------------------------------------

    def name(self):
        return self.env['profile']['name']

    def type(self):
        return self.env['profile']['type']

    def is_switch(self):
        return self.type() == 'Switch'

    def is_compute(self):
        return self.type() == 'Compute'

    def is_io(self):
        return self.type() == 'IO'

    def is_memory(self):
        return self.type() == 'Memory'

# ----------------------------------------------------------------------------------------------------------------------
