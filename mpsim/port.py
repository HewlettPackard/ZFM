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
import copy
import random
import socket

from threading import Lock
from resolve import resolve
from log import Log

# ----------------------------------------------------------------------------------------------------------------------

class Port():
    PORT_DEAD   = 8999
    PORT_OFFSET = 9000

    def __init__(self, node, state, src_port_index, dst_node, dst_port_index, dst_uid):

        dst_port = self.PORT_OFFSET + dst_port_index if state == 'Enabled' else self.PORT_DEAD
        dst_addr, _ = resolve(dst_node)
        src_addr, _ = node.env['profile']['address'].split(':')

        self.node = node
        self.state = state
        self.index = src_port_index
        self.remote_port = 0
        self.remote_uid = 0
        self.training_state = 0
        self.lock = Lock()
        self.remote_addr = (dst_addr, dst_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = socket.gethostbyname(src_addr)

        self.socket.bind((self.address, src_port_index + self.PORT_OFFSET))

# ----------------------------------------------------------------------------------------------------------------------

    def send(self, packet):
        message = json.dumps(packet).encode('utf-8')
        self.socket.sendto(message, self.remote_addr)

# ----------------------------------------------------------------------------------------------------------------------

    def train(self, patch_data, packet_data):
        attribute = self.node.env['attributes'][self.node.port_to_path(self.index)]

        with self.lock:
            if patch_data:
                attribute['Status']['State'] = 'Starting'

                #
                # Send a training packet to my peer
                #
                data = { 'function' : 'train',
                         'UID'      : self.node.env['profile']['UID'],
                         'Port'     : self.index }

                self.send(data)
                self.training_state |= 1

            if packet_data:
                #
                # Save the remote identification.
                #
                self.remote_uid = packet_data['UID']
                self.remote_port = packet_data['Port']
                self.training_state |= 2

            if self.training_state == 3:
                #
                # Bring the port to fully trained status.
                #
                attribute['Oem']['Hpe']['RemoteComponentID']['UID'] = self.remote_uid
                attribute['Oem']['Hpe']['RemoteComponentID']['Port'] = self.remote_port

                attribute['Status']['State'] = 'StandbyOffline'
                attribute['LinkState'] = 'Enabled'

                Log.info('{}/{} trained with {:X} {}', self.node.name(), self.index, self.remote_uid, self.remote_port)


    def detrain(self, patch_data, packet_data):
        Log.info('{}/{} detrained with {:X} {}', self.node.name(), self.index, self.remote_uid, self.remote_port)
        attribute = self.node.env['attributes'][self.node.port_to_path(self.index)]

        with self.lock:
            self.training_state = 0

            if patch_data:
                #
                # Send a detraining packet to my peer
                #
                data = { 'function' : 'detrain' }
                self.send(data)

            #
            # We are down now.
            #
            attribute['Oem']['Hpe']['RemoteComponentID'] = { 'UID' : 0, 'Port' : 0 }
            attribute['Status']['State'] = 'Disabled'
            attribute['LinkState'] = 'Disabled'
            attribute['InterfaceState'] = 'Disabled'


# ----------------------------------------------------------------------------------------------------------------------

    #
    # Training packet handler.
    #
    def train_request(self, packet, address):
        self.train(None, packet)


    def detrain_request(self, packet, address):
        self.detrain(None, packet)


    #
    # Port based global packet handler.
    #
    def process_request(self):
        message, address = self.socket.recvfrom(65536)
        packet = json.loads(message.decode('utf-8'))
        function = packet.get('function', None)

        if function == 'train':
            self.train_request(packet, address)
        elif function == 'detrain':
            self.detrain_request(packet, address)
        elif function:
            Log.info('unknown function : {}'.format(function))
        else:
            Log.info('no function')

# ----------------------------------------------------------------------------------------------------------------------

    def port_metrics_attribute(self):
        node = self.node

        port_path = node.port_to_path(self.index)
        port_attribute = node.env['attributes'][node.port_to_path(self.index)]

        metrics_path = port_attribute['Metrics']['@odata.id']
        metrics_attribute = node.env['attributes'][metrics_path]

        return port_attribute, metrics_attribute



    def reset_port_statistics(self):
        port_attribute, metrics_attribute = self.port_metrics_attribute()
        oem_metrics = metrics_attribute['Oem']['Hpe']['Metrics']

        #
        # Port Interface statistics.
        #
        interface_metrics = metrics_attribute['Gen-Z']
        for error_name in interface_metrics:
            interface_metrics[error_name] = 0

        #
        # Port Requestor/Responder statistics.
        #
        request_metrics = oem_metrics.get('Request', None)
        if request_metrics:
            request_metrics['XmitCount'] = 0
            request_metrics['XmitBytes'] = 0
            request_metrics['RecvCount'] = 0
            request_metrics['RecvBytes'] = 0

        response_metrics = oem_metrics.get('Response', None)
        if response_metrics:
            response_metrics['XmitCount'] = 0
            response_metrics['XmitBytes'] = 0
            response_metrics['RecvCount'] = 0
            response_metrics['RecvBytes'] = 0

        #
        # Port VC statistics.
        #
        vc_metrics = oem_metrics.get('VC0', None)
        if vc_metrics:
            for vc_index in range(16):
                vc_metrics = oem_metrics['VC{}'.format(vc_index)]

                vc_metrics['XmitCount'] = 0
                vc_metrics['XmitBytes'] = 0
                vc_metrics['RecvCount'] = 0
                vc_metrics['RecvBytes'] = 0
                vc_metrics['Occupancy'] = 0


    def update_port_statistics(self):
        port_attribute, metrics_attribute = self.port_metrics_attribute()
        oem_metrics = metrics_attribute['Oem']['Hpe']['Metrics']

        if port_attribute['InterfaceState'] == 'Enabled':   # the True is just for demonstration

            #
            # Port Interface statistics.
            #
            interface_metrics = metrics_attribute['Gen-Z']
            for error_name in interface_metrics:
                interface_metrics[error_name] += int(random.uniform(0,1.05))

            #
            # Port Requestor/Responder statistics.
            #
            msg_probs = [ random.randint(0,3) > 0 for i in range(4) ]

            request_metrics = oem_metrics.get('Request', None)
            if request_metrics:
                if msg_probs[0]:
                    request_metrics['XmitCount'] += 1
                    request_metrics['XmitBytes'] += random.randint(1,256)
                if msg_probs[1]:
                    request_metrics['RecvCount'] += 1
                    request_metrics['RecvBytes'] += random.randint(1,256)

            response_metrics = oem_metrics.get('Response', None)
            if response_metrics:
                if msg_probs[2]:
                    response_metrics['XmitCount'] += 1
                    response_metrics['XmitBytes'] += random.randint(1,256)
                if msg_probs[3]:
                    response_metrics['RecvCount'] += 1
                    response_metrics['RecvBytes'] += random.randint(1,256)

            #
            # Port VC statistics.
            #
            vc_metrics = oem_metrics.get('VC0', None)
            if vc_metrics:
                if any(msg_probs):
                    vc_index = random.randint(0,15)
                    vc_metrics = oem_metrics['VC{}'.format(vc_index)]

                    if msg_probs[0] or msg_probs[2]:
                        vc_metrics['XmitCount'] += 1
                        vc_metrics['XmitBytes'] += random.randint(0,256)
                    if msg_probs[1] or msg_probs[3]:
                        vc_metrics['RecvCount'] += 1
                        vc_metrics['RecvBytes'] += random.randint(0,256)

                    vc_metrics['Occupancy'] += random.randint(0,1)

# ----------------------------------------------------------------------------------------------------------------------

    #
    # PATCH trigger function.  If specific fields in the port attribute are being set, then they can trigger
    # actions which affect the port state.
    #
    def trigger(self, attribute, data):

        #
        # Patching LinkState can trigger port training.
        #
        if 'LinkState' in data:
            if attribute['LinkState'] == 'Disabled' and data['LinkState'] == 'Enabled':
                self.train(data, None)
            elif attribute['LinkState'] == 'Enabled' and data['LinkState'] == 'Disabled':
                self.detrain(data, None)

            attribute['LinkState'] = data['LinkState']
            del data['LinkState']

        #
        # If InterfaceState is being changed, then the port can become enabled.
        #
        if 'InterfaceState' in data:
            if attribute['InterfaceState'] == 'Disabled' and data['InterfaceState'] == 'Enabled':
                attribute['Status']['State'] = 'Enabled'
            elif data['InterfaceState'] == 'Disabled':
                self.reset_port_statistics()

            attribute['InterfaceState'] = data['InterfaceState']
            del data['InterfaceState']

# ----------------------------------------------------------------------------------------------------------------------

    #
    # Convenience functions.
    #
    def is_enabled(self):
        return self.state == 'Enabled'

# ----------------------------------------------------------------------------------------------------------------------
