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
import random

from queue import Queue
from queue import Empty
from threading import Thread

# ----------------------------------------------------------------------------------------------------------------------

class Node():

    def __init__(self, server):
        #
        # The cache contains all of the attribute/value pairs.
        #
        self.server = server
        self.port_range = [ i for i in range(self.server.profile['portStart'], self.server.profile['portEnd']) ]

        #
        # Create an async queue for requests.
        #
        self.queue = Queue()

        #
        # Create a thread to process aysnc requests.
        #
        self.processor = Thread(target=self.run, daemon=True)
        self.processor.start()

# ----------------------------------------------------------------------------------------------------------------------

    def update_common(self, key, old_data, new_data):
        if type(old_data[key]) is dict and type(new_data[key]) is dict:
            self.update_dict(old_data[key], new_data[key])
        elif type(old_data[key]) is list and type(new_data[key]) is list:
            self.update_list(old_data[key], new_data[key])
        else:
            old_data[key] = copy.deepcopy(new_data[key])


    def update_list(self, old_data, new_data):
        for i in range(len(new_data)):
            if i >= len(old_data):
                old_data.append(copy.deepcopy(new_data[i]))
            else:
                self.update_common(i, old_data, new_data)


    def update_dict(self, old_data, new_data):
        for key in new_data:
            if key not in old_data:
                old_data[key] = copy.deepcopy(new_data[key])
            else:
                self.update_common(key, old_data, new_data)


    def update_resource(self, old_data, new_data):
        self.update_dict(old_data, new_data)

# ----------------------------------------------------------------------------------------------------------------------

    #
    # REST interface functions.
    #
    def do_PATCH(self, base_name, data):
        attribute_data = self.server.cache[base_name]
        self.trigger(base_name, data)
        self.update_resource(attribute_data, data)

# ----------------------------------------------------------------------------------------------------------------------

    def reset_port_statistics(self, port_attribute):

        #
        # Get metrics path.
        #
        metrics_path = port_attribute['Metrics']['@odata.id']
        metrics_attribute = self.server.cache[metrics_path]
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

        #
        # Get the port number
        #
        port_list = self.server.profile['ports']
        for index,info in enumerate(port_list):
            port_path = self.port_to_path(index)
            port_attr = self.server.cache[port_path]

            #
            # Check port state.
            #
            if info['State'] != 'Enabled':
                continue
            if port_attr['LinkState'] != 'Enabled':
                continue
            if port_attr['InterfaceState'] != 'Enabled':
                continue

            #
            # Get metrics path.
            #
            metrics_path = port_attr['Metrics']['@odata.id']
            metrics_attr = self.server.cache[metrics_path]
            oem_metrics = metrics_attr['Oem']['Hpe']['Metrics']

            #
            # Port Interface statistics.
            #
            interface_metrics = metrics_attr['Gen-Z']
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
    # Thread functions.
    #
    def enqueue(self, args):
        self.queue.put(args)


    def dequeue(self):
        work_item = None
        try:
            work_item = self.queue.get(True, 1)
        except Empty:
            pass

        return work_item


    def run(self):
        while True:
            work_item = self.dequeue()
            if work_item:
                function = work_item[0]
                args = work_item[1:]
                function(*args)
            else:
                self.update_port_statistics()

# ----------------------------------------------------------------------------------------------------------------------

    #
    # Common PATCH functions.
    #
    def port_trigger(self, base_name, data):
        port_attribute = self.server.cache[base_name]

        #
        # Get the port number
        #
        port_number = self.path_to_port(base_name)
        if port_number < 0:
            return

        port_profile = self.server.profile['ports'][port_number]
        if port_profile['State'] != 'Enabled':
            return

        #
        # Patching LinkState can trigger port training.
        #
        if 'LinkState' in data:
            if port_attribute['LinkState'] == 'Disabled' and data['LinkState'] == 'Enabled':
                port_attribute['Status']['State'] = 'Starting'
                self.enqueue([self.link_train_continue, base_name, port_number, time.time()])
            elif port_attribute['LinkState'] == 'Enabled' and data['LinkState'] == 'Disabled':
                port_attribute['Oem']['Hpe']['RemoteComponentID'] = { 'UID' : 0, 'Port' : 0 }

            port_attribute['LinkState'] = data['LinkState']
            del data['LinkState']

        #
        # If InterfaceState is being changed, then the port can become enabled.
        #
        if 'InterfaceState' in data:
            if data['InterfaceState'] == 'Enabled':
                self.enqueue([self.interface_train_continue, base_name, port_number, time.time()])
            elif data['InterfaceState'] == 'Disabled':
                self.reset_port_statistics(port_attribute)

            port_attribute['InterfaceState'] = data['InterfaceState']
            del data['InterfaceState']


    def link_train_continue(self, *args):
        base_name, port_number, start_time = args
        port_attribute = self.server.cache[base_name]

        #
        # Check the port profile.
        #
        port_profile = self.server.profile['ports'][port_number]
        if port_profile['State'] != 'Enabled':
            return

        #
        # Wait for 2 seconds to simulate training complete.
        #
        if (time.time() - start_time) < 2.0:
            self.enqueue([self.link_train_continue, base_name, port_number, start_time])
            return

        #
        # Update the remote component id.
        #
        port_attribute['Oem']['Hpe']['RemoteComponentID'] = port_profile['Remote']

        #
        # Update the port status and link state.
        #
        port_attribute['Status']['State'] = 'StandbyOffline'
        port_attribute['LinkState'] = 'Enabled'


    def interface_train_continue(self, *args):
        base_name, port_number, start_time = args
        port_attribute = self.server.cache[base_name]

        #
        # Check the port profile.
        #
        port_profile = self.server.profile['ports'][port_number]
        if port_profile['State'] != 'Enabled':
            return

        #
        # Wait for 1 second to simulate interface enablement.
        #
        if (time.time() - start_time) < 1.0:
            self.enqueue([self.interface_train_continue, base_name, port_number, start_time])
            return

        #
        # Update the port status.
        #
        port_attribute['Status']['State'] = 'Enabled'

# ----------------------------------------------------------------------------------------------------------------------
