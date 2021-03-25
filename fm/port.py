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
import datetime

from km.fm.log      import Log
from enum           import Enum
from km.fm.routeset import LPRT
from km.fm.routeset import MPRT
from km.fm.vcat     import VCAT
from km.fm.metrics  import Metrics

# ----------------------------------------------------------------------------------------------------------------------

class Port():

    def __init__(self, node, index, name):

        #
        # Get the port attributes and check its health.
        #
        self.node = node
        self.name = name
        self.index = index
        self.active = node.port_states[index]['State'] == 'Enabled'
        self.configuration = node.configuration[name]

        if self.active:
            self.remote_uid  = node.port_states[index]['Remote']['UID']
            self.remote_port = node.port_states[index]['Remote']['Port']

        genz_attributes = self.configuration.get('Gen-Z', None)

        if genz_attributes:
            if 'LPRT' in genz_attributes: self.lprt = LPRT(node, genz_attributes['LPRT']['@odata.id'])
            if 'MPRT' in genz_attributes: self.mprt = MPRT(node, genz_attributes['MPRT']['@odata.id'])
            if 'VCAT' in genz_attributes: self.vcat = VCAT(node, genz_attributes['VCAT']['@odata.id'])

        #
        # Setup the Metrics.
        #
        metrics_attributes = self.configuration.get('Metrics', None)
        if metrics_attributes:
            self.metrics = Metrics(node, self, metrics_attributes['@odata.id'])


    def query(self):
        #
        # Get the port attribute.  Update the current view.
        #
        status,attr = self.node.get(self.name)
        if status:
            self.current = attr
        else:
            Log.error('failed to get {}/{} attributes', self.node.name, self.index)

        return status


    def query_all(self):
        metric_attr = None

        #
        # Get the port and metric attributes.  Update the current view.
        #
        status = self.query()
        if status:
            status,attr = self.metrics.get()
            if status:
                metric_attr = {}
                metric_attr['Interface'] = attr['Gen-Z']

                try:
                    metric_attr['Request']   = attr['Oem']['Hpe']['Metrics']['Request']
                    metric_attr['Response']  = attr['Oem']['Hpe']['Metrics']['Response']
                except:
                    metric_attr.pop('Request', None)
                    metric_attr.pop('Response', None)

                try:
                    for vc in range(16):
                        vc_name = 'VC{}'.format(vc)
                        metric_attr[vc_name] = attr['Oem']['Hpe']['Metrics'][vc_name]
                except:
                    for vc in range(16):
                        vc_name = 'VC{}'.format(vc)
                        metric_attr.pop(vc_name, None)

                self.current_metrics = metric_attr

        return status

# ----------------------------------------------------------------------------------------------------------------------

    def is_trained(self):
        #
        #
        # Make sure that this port is enabled.
        #
        if not self.query():
            Log.error('{}[{}].train : can\'t read status', self.node.name, self.index)
            self.active = False
            return False

        state, health = self.current['Status']['State'], self.current['Status']['Health']

        #
        # Check the port health.
        #
        if health != 'OK':
            Log.error('{}[{}].train : port health {} is bad', self.node.name, self.index, health)
            self.active = False
            return False

        #
        # Check the state.
        #
        if   state == 'Disabled':
            return False
        elif state == 'Starting':
            return False
        elif state == 'StandbyOffline':
            return True
        elif state == 'Enabled':
            return True
        else:
            Log.error('{}[{}].train : port state {} is bad', self.node.name, self.index, state)
            self.active = False
            return False


    def train(self):

        #
        #
        # Make sure that this port is enabled.
        #
        if not self.query():
            Log.error('{}[{}].train : can\'t read status', self.node.name, self.index)
            self.active = False
            return False

        state, health = self.current['Status']['State'], self.current['Status']['Health']
        link_state = self.current['LinkState']
        if_state = self.current['InterfaceState']
        Log.debug('{}[{}].train : S={}/{}  LS={}  IF={}', self.node.name, self.index, state, health, link_state, if_state)

        #
        # Check the port health.
        #
        if health != 'OK':
            Log.error('{}[{}].train : port health {} is bad', self.node.name, self.index, health)
            self.active = False
            return False

        #
        # Check the port state for consistency.
        #
        possible_port_states = {
            # Status             Link         Interface

            ('Disabled',        'Disabled',  'Disabled')   : True,
            ('Starting',        'Disabled',  'Disabled')   : False,     # link != Enabled
            ('StandbyOffline',  'Disabled',  'Disabled')   : False,     # link != Enabled
            ('Enabled',         'Disabled',  'Disabled')   : False,     # link != Enabled

            ('Disabled',        'Disabled',  'Enabled')    : False,     # interface != Disabled
            ('Starting',        'Disabled',  'Enabled')    : False,     # link != Enabled
            ('StandbyOffline',  'Disabled',  'Enabled')    : False,     # link != Enabled
            ('Enabled',         'Disabled',  'Enabled')    : False,     # link != Enabled

            ('Disabled',        'Enabled',   'Disabled')   : False,     # status != Starting
            ('Starting',        'Enabled',   'Disabled')   : True,
            ('StandbyOffline',  'Enabled',   'Disabled')   : True,
            ('Enabled',         'Enabled',   'Disabled')   : False,     # interface != Enabled

            ('Disabled',        'Enabled',   'Enabled')    : False,     # link != Disabled
            ('Starting',        'Enabled',   'Enabled')    : False,     # interface != Disabled
            ('StandbyOffline',  'Enabled',   'Enabled')    : True,
            ('Enabled',         'Enabled',   'Enabled')    : True,
        }

        port_state = possible_port_states.get((state, link_state, if_state), False)
        if not port_state:
            Log.error('{}[{}].train : invalid port state {} {} {}', self.node.name, self.index, state, link_state, if_state)
            return False

        #
        # Only train up if we are in the correct state.
        #
        if state == 'Disabled' and link_state == 'Disabled' and if_state == 'Disabled':
            status, _ = self.node.patch(self.name, { 'LinkState' : 'Enabled' })
            if not status:
                Log.error('{}[{}].train : can\'t set LinkState', self.node.name, self.index)
                self.active = False
                return False

        return True

# ----------------------------------------------------------------------------------------------------------------------

    def validate(self):
        if not self.query():
            Log.error('{}[{}].validate : can\'t fetch attributes - downing port', self.node.name, self.index)
            self.active = False
            return False

        #
        # Get the node's view of its remote neighbor
        #
        attr_uid  = self.current['Oem']['Hpe']['RemoteComponentID']['UID']
        attr_port = self.current['Oem']['Hpe']['RemoteComponentID']['Port']

        #
        # Compare it to our view.
        #
        status = (attr_uid == self.remote_uid) and (attr_port == self.remote_port)
        if not status:
            Log.error('{}[{}] didn\'t validate: 0x{:X}:{:<2} vs 0x{:X}:{:<2}',
                        self.node.name, self.index,
                        self.remote_uid, self.remote_port,
                        attr_uid, attr_port)
            self.active = False
            return False

        return True

# ----------------------------------------------------------------------------------------------------------------------

    def load(self):
        status = True
        if self.lprt: status &= self.lprt.patch()
        if self.mprt: status &= self.mprt.patch()
        if self.vcat: status &= self.vcat.patch()
        if self.metrics: status &= self.metrics.reset()

        if not status:
            Log.error('{}[{}].load : can\'t load attributes - downing port', self.node.name, self.index)
            self.active = False

        return status

# ----------------------------------------------------------------------------------------------------------------------

    def is_enabled(self):

        #
        #
        # Make sure that this port is enabled.
        #
        if not self.query():
            Log.error('{}[{}].enable : can\'t read status', self.node.name, self.index)
            self.active = False
            return False

        state, health = self.current['Status']['State'], self.current['Status']['Health']
        link_state = self.current['LinkState']
        if_state = self.current['InterfaceState']

        if health != 'OK':
            Log.error('{}[{}].enable : port health {} is bad', self.node.name, self.index, health)
            port.active = False
            return False

        if state != 'Enabled':
            Log.debug('{}[{}].enable : state not yet ready {}/{}', self.node.name, self.index, state, health)
            return False

        if if_state != 'Enabled':
            Log.debug('{}[{}].enable : interface not yet enabled {}', self.node.name, self.index, if_state)
            return False

        return True


    def enable(self):

        #
        #
        # Get the current port state.
        #
        if not self.query():
            Log.error('{}[{}].enable : can\'t read status', self.node.name, self.index)
            self.active = False
            return False

        state, health = self.current['Status']['State'], self.current['Status']['Health']
        link_state = self.current['LinkState']
        if_state = self.current['InterfaceState']

        if health != 'OK':
            Log.error('{}[{}].enable : port health {} is bad', self.node.name, self.index, health)
            port.active = False
            return False

        #
        # Verify that the port is in the correct state for enabling the interface.
        #
        if state == 'Enabled':
            Log.debug('{}[{}].enable : already enabled {}/{}', self.node.name, self.index, state, health)
            return True

        if state != 'StandbyOffline':
            Log.debug('{}[{}].enable : state not ready {}/{}', self.node.name, self.index, state, health)
            return False

        if link_state != 'Enabled':
            Log.debug('{}[{}].enable : link state not ready {}', self.node.name, self.index, link_state)
            return False

        if if_state != 'Disabled':
            Log.debug('{}[{}].enable : interface state not ready {}', self.node.name, self.index, if_state)
            return False

        #
        # If we are in StandbyOffline mode, transition to Enabled.
        #
        values = { 'InterfaceState' : 'Enabled' }
        status, _ = self.node.patch(self.name, values)
        if not status:
            Log.error('{}[{}].enable : can\'t enable interface - downing port', self.node.name, self.index)
            self.active = False

        Log.debug('{}[{}].enable : status={}', self.node.name, self.index, status)
        return status

# ----------------------------------------------------------------------------------------------------------------------

    def sweep(self):

        #
        # Read the port metrics.
        #
        status = self.metrics.check()
        if not status:
            Log.error('{}[{}].sweep : can\'t read metrics - downing port', self.node.name, self.index)
            self.active = False
            return status

        #
        # Check the port state.  If the link state is good and the interface state is bad, then it is
        # possible that someone is resetting some metrics.  (You do this by resetting the interface.)
        # So in this case, we sleep for two seconds to allow the interface to be good again.
        #
        link_state, if_state = self.link_interface_state()

        if (link_state == 'Enabled') and (if_state == 'Disabled'):
            time.sleep(2)
            link_state, if_state = self.link_interface_state()

        status = (link_state == 'Enabled') and (if_state == 'Enabled')
        if not status:
            Log.error('{}[{}].sweep : link/interface in bad state - downing port', self.node.name, self.index)
            self.active = False

        return status

# ----------------------------------------------------------------------------------------------------------------------

    def status_is_starting(self):
        return self.current['Status']['State'] == 'Starting' and self.current['Status']['Health'] == 'OK'


    def status_is_standing_by(self):
        return self.current['Status']['State'] == 'StandbyOffline' and self.current['Status']['Health'] == 'OK'


    def status_is_disabled(self):
        return self.current['Status']['State'] == 'Disabled' and self.current['Status']['Health'] == 'OK'


    def status_is_enabled(self):
        return self.current['Status']['State'] == 'Enabled' and self.current['Status']['Health'] == 'OK'

# ----------------------------------------------------------------------------------------------------------------------

    def link_interface_state(self):
        if self.query():
            return (self.current['LinkState'], self.current['InterfaceState'])
        else:
            return ('Unknown', 'Unknown')

# ----------------------------------------------------------------------------------------------------------------------

    def GET_port(self, parameters):
        node = self.node

        #
        # Fetch the port attribute.
        #
        metric_attr = self.query_all()
        if not metric_attr:
            Log.error('can\'t retrieve port attribute for {}', self.name)
            return 404, None

        #
        # We now have the port attribute.
        #
        oem_data = self.current['Oem']['Hpe']

        data = { 'DataType'       : 'PORT',
                 'Timestamp'      : datetime.datetime.now().isoformat(),
                 'Node'           : node.profile['name'],
                 'Hostname'       : node.name,
                 'Index'          : self.index,
                 'ConfigState'    : 'Enabled' if self.active else 'Disabled',
                 'Status'         : '{}/{}'.format(self.current['Status']['State'], self.current['Status']['Health']),
                 'LinkState'      : self.current['LinkState'],
                 'InterfaceState' : self.current['InterfaceState'],
                 'Remote'         : '0x{:08X}/{:<2}'.format(oem_data['RemoteComponentID']['UID'], oem_data['RemoteComponentID']['Port']),
                 'Metrics'        : self.current_metrics
        }

        return 200, data

# ----------------------------------------------------------------------------------------------------------------------

    def GET(self,parameters):
        return self.GET_port(parameters)

# ----------------------------------------------------------------------------------------------------------------------
