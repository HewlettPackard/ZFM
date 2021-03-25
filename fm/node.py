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
import copy
import glob
import socket
import datetime
import multiprocessing

from enum      import Enum
from queue     import Queue
from threading import Thread

from km.fm.log     import Log
from km.fm.port    import Port
from km.fm.rest    import Rest
from km.fm.chassis import Chassis

# ----------------------------------------------------------------------------------------------------------------------

class WIStatus(Enum):
    IDLE        = 1         # Not started yet
    BUSY        = 2         # Busy processing
    SUCCESS     = 3         # Completed and successful
    FAILURE     = 4         # Completed and failed

# ----------------------------------------------------------------------------------------------------------------------

class Node():

    def __init__(self, name, profile):

        #
        # Save the attributes.
        #
        self.name = name
        self.type = profile['type']
        self.active = profile['Active'] == 'Enabled'
        self.address = profile['address']
        self.uid = profile['UID']
        self.gcids = profile['GCIDs']
        self.asicid = profile['AsicID']['ComponentID']
        self.geoid = profile['GeoID']
        self.topoid = profile['TopoID']
        self.port_states = profile['ports']
        self.num_ports = len(profile['ports'])
        self.profile = profile

        address, sep, port = profile['address'].partition(':')
        try:
            hostaddr = socket.gethostbyname(address)
            if not port: port = '8081'
            profile['address'] = hostaddr + ':' + port
        except:
            Log.error('{} : can\'t resolve hostname {} - disabling node', self.name, profile['address'])
            self.active = False

        port_string = ''
        for index, data in enumerate(profile['ports']):
            port_string += '1' if data['State'] == 'Enabled' else '0'

        Log.debug('{} : active port mask = {}', self.name, port_string)

        #
        # Initialize work item statuses.
        #
        self.inited = WIStatus.IDLE
        self.trained = WIStatus.IDLE
        self.validated = WIStatus.IDLE
        self.loaded = WIStatus.IDLE
        self.enabled = WIStatus.IDLE
        self.swept = WIStatus.IDLE

        #
        # Load the attributes.
        #
        with open(profile['attributes']) as f:
            self.configuration = json.load(f)

        #
        #
        # Create a work queue.
        #
        self.queue = Queue()

        #
        # Start the thread.
        #
        self.worker = Thread(target=self.run, daemon=True)
        self.worker.start()

        #
        # Get the chassis.
        #
        chassis_attr_name = self.configuration['/redfish/v1/Chassis']['Members'][0]['@odata.id']
        self.chassis = Chassis(self, chassis_attr_name)

# ----------------------------------------------------------------------------------------------------------------------

    def create_ports(self, port_attr_names):

        self.ports = []
        for i,attr_name in enumerate(port_attr_names):
            self.ports.append(Port(self, i, attr_name))

# ----------------------------------------------------------------------------------------------------------------------

    def get(self, name):
        return Rest.get(self, name)

    def patch(self, name, value):
        return Rest.patch(self, name, value)

# ----------------------------------------------------------------------------------------------------------------------

    def init_endpoints(self):

        for index,gcid in enumerate(self.gcids):
            cid = (gcid % 4096)
            sid = (gcid // 4096) % 65536

            attribute = '/redfish/v1/Fabrics/GenZ/Endpoints/{}'.format(index+1)
            values = { 'ConnectedEntities' : [ { 'GCID' : { 'ComponentID' : cid, 'SubnetID' : sid }} ],
                       'Oem': { 'Hpe': { 'UID': self.uid }}
            }

            status, _ = Rest.patch(self, attribute, values)
            if not status:
                return status

        return True

# ----------------------------------------------------------------------------------------------------------------------

    def is_powered_on(self):
        return self.chassis.ready()

# ----------------------------------------------------------------------------------------------------------------------

    def is_telemetry_on(self):
        status, attr = Rest.get(self, '/redfish/v1/TelemetryService')
        if status:
            return attr['Oem']['Hpe']['ServiceEnabled']
        else:
            return False


    def is_telemetry_off(self):
        return not self.is_telemetry_on()


    def turn_telemetry_off(self):
        attr = { "Oem": { "Hpe": { "ServiceEnabled": False } } }
        status = Rest.patch(self, '/redfish/v1/TelemetryService', attr)

        return status


    def turn_telemetry_on(self):
        attr = { "Oem": { "Hpe": { "ServiceEnabled": True } } }
        status = Rest.patch(self, '/redfish/v1/TelemetryService', attr)

        return status

# ----------------------------------------------------------------------------------------------------------------------

    def done_status(self, status):
        if status == WIStatus.SUCCESS:
            return 1
        elif status == WIStatus.FAILURE:
            return 0
        else:
            return -1

# ----------------------------------------------------------------------------------------------------------------------

    def do_active(self, function):
        #
        # Execute the given function name on all of the active ports.  It returns True if
        # every function succeeds else False.
        #
        return all(getattr(port, function)() for port in self.ports if port.active)


    def do_child_active(self, function, stdout):
        status = self.do_active(function)
        stdout.send(status)
        stdout.close()


    def do_mp_active(self, function):
        stdin, stdout = multiprocessing.Pipe()
        process = multiprocessing.Process(target=self.do_child_active, name=self.name, args=(function,stdout))
        process.daemon = True
        process.start()
        status = stdin.recv()
        process.join()
        stdin.close()

        return status

# ----------------------------------------------------------------------------------------------------------------------

    def init_done(self):
        return self.done_status(self.inited)


    def init(self, args, kwargs):
        self.inited = WIStatus.BUSY

        #
        # Check the chassis status.  (Power must be on and status Enabled/OK.)
        #
        if not self.chassis.ready():
            Log.error('{} : chassis is not ready', self.name)
            self.inited = WIStatus.FAILURE
            return

        #
        # Set the endpoint GCIDs and UIDs
        #
        status = self.init_endpoints()

        if not status:
            Log.error('{} : failed to init endpoint GCID and UID', self.name)

        self.inited = WIStatus.SUCCESS if status else WIStatus.FAILURE
        return self.init_done()

# ----------------------------------------------------------------------------------------------------------------------

    def train_done(self):
        return self.done_status(self.trained)


    def train(self, args, kwargs):
        self.trained = WIStatus.BUSY

        #
        # Check the chassis status.  (Power must be on and status Enabled/OK.)
        #
        if not self.chassis.ready():
            Log.error('{} : chassis is not ready', self.name)
            self.trained = WIStatus.FAILURE
            return

        #
        # Train the ports one at a time.
        #
        if not self.do_active('train'):
            Log.error('{} : ports didn\'t train', self.name)
            self.trained = WIStatus.FAILURE
            return False

        #
        # Wait for Port.Status to transition to StandbyOffline.
        # If the ports don't transition in 200 seconds, then call it quits.
        #
        retries = 0
        status = False
        max_retries = kwargs['retries']
        while (retries < max_retries) and (not status):
            retries += 1
            status = self.do_active('is_trained')
            time.sleep(1)

        if (retries >= max_retries) and (not status):
            Log.error('{} : timed out waiting for ports to train', self.name)

        self.trained = WIStatus.SUCCESS if status else WIStatus.FAILURE
        if not status:
            s = ''.join([ '-' if not port.active else '1' if port.is_trained() else '0' ])
            Log.error('{} : ports didn\'t train : {}', self.name, s)

        return self.train_done()

# ----------------------------------------------------------------------------------------------------------------------

    def validate_done(self):
        return self.done_status(self.validated)


    def validate(self, args, kwargs):
        self.validated = WIStatus.BUSY

        #
        # Check that the remote sides are consistent with the static configuration.
        #
        status = self.do_active('validate')

        #
        # Check the final status.
        #
        self.validated = WIStatus.SUCCESS if status else WIStatus.FAILURE
        if not status:
            Log.error('{} : ports didn\'t validate', self.name)

        return self.validate_done()

# ----------------------------------------------------------------------------------------------------------------------

    def load_done(self):
        return self.done_status(self.loaded)


    def load(self, args, kwargs):
        self.loaded = WIStatus.BUSY

        #
        # Load the port attributes.
        #
        status = self.do_mp_active('load')
        Log.debug('{} : port load done', self.name)

        #
        # Load the node specific attributes.
        #
        status &= self.load_specific(args, kwargs)
        Log.debug('{} : node load done', self.name)

        #
        # Check the final status.
        #
        self.loaded = WIStatus.SUCCESS if status else WIStatus.FAILURE
        if not status:
            Log.error('{} : ports didn\'t load', self.name)

        return self.load_done()

# ----------------------------------------------------------------------------------------------------------------------

    def enable_done(self):
        return self.done_status(self.enabled)


    def enable(self, args, kwargs):
        self.enabled = WIStatus.BUSY

        #
        # Patch the InterfaceState.
        #
        if not self.do_active('enable'):
            Log.error('{} : ports didn\'t enable', self.name)
            self.enabled = WIStatus.FAILURE
            return False

        #
        # Wait for Port.Status to transition to Enabled.
        # If the ports don't transition in 20 seconds, then call it quits.
        #
        retries = 0
        status = False
        max_retries = kwargs['retries']
        while (retries < max_retries) and (not status):
            retries += 1
            time.sleep(1)
            status = self.do_active('is_enabled')

        if (retries >= max_retries) and (not status):
            Log.error('{} : timed out waiting for ports to enable', self.name)

        #
        # Check the final status.
        #
        self.enabled = WIStatus.SUCCESS if status else WIStatus.FAILURE
        if not status:
            Log.error('{} : ports didn\'t enable', self.name)

        Log.debug('{} : enable status = {}', self.name, self.enable_done())
        return self.enable_done()

# ----------------------------------------------------------------------------------------------------------------------

    def sweep_done(self):
        return self.done_status(self.swept)


    def sweep(self, args, kwargs):
        self.swept = WIStatus.BUSY

        sweep_type = args[0]

        #
        # Check the chassis power.
        #
        if not self.is_powered_on():
            Log.error('{} : is not powered on', self.name)
            self.swept = WIStatus.FAILURE
            return self.sweep_done()

        #
        # 'light' sweep is now done.
        #
        if sweep_type == 'light':
            self.swept = WIStatus.SUCCESS
            return self.sweep_done()

        #
        # 'medium' sweeps need Telemetry Services off.
        # 'heavy' sweeps will turn Telemetry Services off.
        #
        telemetry_was_on = self.is_telemetry_on()
        if sweep_type == 'heavy' and telemetry_was_on:
            self.turn_telemetry_off()
            time.sleep(3)

        #
        # Read metrics.
        #
        status = True
        if self.is_telemetry_off():
            status = self.do_active('sweep')

        #
        # Turn telemetry back on (if it was previously on).
        #
        if sweep_type == 'heavy' and telemetry_was_on:
            self.turn_telemetry_on()

        #
        # Check the final status.
        #
        if status:
            self.swept = WIStatus.SUCCESS
        else:
            Log.error('{} : didn\'t sweep', self.name)
            self.swept = WIStatus.FAILURE

        return self.sweep_done()

# ----------------------------------------------------------------------------------------------------------------------

    def enqueue(self, command, args, kwargs):
        self.queue.put((command, args, kwargs))


    def dequeue(self):
        return self.queue.get()

# ----------------------------------------------------------------------------------------------------------------------

    def run(self):

        while True:
            command, args, kwargs = self.dequeue()
            function = getattr(self, command, None)
            if function:
                function(args, kwargs)
            else:
                Log.error('invalid request [{}]', command)

# ----------------------------------------------------------------------------------------------------------------------

    def GET_node(self, parameters):
        profile = self.profile

        #
        # Node level attributes.
        #
        chassis = self.configuration['/redfish/v1/Chassis/1']
        location = chassis['Oem']['Hpe']['Location']
        config_state = profile['Active']
        power_state = chassis['PowerState']
        status = '{}/{}'.format(chassis['Status']['State'], chassis['Status']['Health'])
        geo_id = '{}:{}:{}:{}'.format(location['RackID'], location['ChassisID'], location['SlotID'], location['NodeID'])

        #
        # For enabled nodes, all the fields should be valid.
        #
        data = { 'DataType'  : 'NODE',
                 'Timestamp' : datetime.datetime.now().isoformat(),
                 'Ports'     : {}
        }

        data['Name']         = profile['name']
        data['Hostname']     = profile['hostname']
        data['FQDN']         = profile['FQDN']
        data['ConfigState']  = config_state
        if config_state == 'Enabled':
            data['PowerState'] = power_state
            data['Status']     = status
            data['UID']        = profile['UID']
            data['TopoID']     = profile['TopoID']
            data['GeoID']      = geo_id
            data['AsicID']     = profile['AsicID']['ComponentID']

            node_ports = data['Ports']
            for i in range(profile['portStart'], profile['portEnd']):
                port = self.ports[i]
                port.query()

                port_state   = port.current['Status']['State']
                port_health  = port.current['Status']['Health']
                link_state   = port.current['LinkState']
                if_state     = port.current['InterfaceState']
                config_state = self.profile['ports'][i]['State']
                port_status  = '{}/{}'.format(port_state, port_health)
                remote_info  = '0x{:08X}/{:<2}'.format(port.remote_uid, port.remote_port) if port.active else ''

                if 'config' in parameters and 'Enabled' in parameters['config'] and config_state != 'Enabled':
                    continue
                if 'interface' in parameters and 'Enabled' in parameters['interface'] and if_state != 'Enabled':
                    continue

                node_ports[i] = { 'ConfigState'    : config_state,
                                  'Status'         : port_status,
                                  'LinkState'      : link_state,
                                  'InterfaceState' : if_state,
                                  'Remote'         : remote_info
                }

        return 200, data

# ----------------------------------------------------------------------------------------------------------------------

    def GET(self,parameters):
        return self.GET_node(parameters)

# ----------------------------------------------------------------------------------------------------------------------

