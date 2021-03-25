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
from km.fm.metrics import Metrics

# ----------------------------------------------------------------------------------------------------------------------

class ZFMFormatter():

    def __init__(self):

        self.delimiters = { 'BROWSER' : ('<pre>', '<pre/>', '<br/>'),
                            'ASCII'   : ('',      '',       '\n'   ),
                            'JSON'    : ('',      '',       ''     ),
        }

        self.funcs = { 'FABRIC' : { 'BROWSER' : self.f_browser, 'ASCII' : self.f_human, 'JSON' : self.f_machine },
                       'NODE'   : { 'BROWSER' : self.n_browser, 'ASCII' : self.n_human, 'JSON' : self.n_machine },
                       'PORT'   : { 'BROWSER' : self.p_browser, 'ASCII' : self.p_human, 'JSON' : self.p_machine },
        }


    def format(self, data, consumer):
        data_type = data.get('DataType', None)

        if consumer not in self.delimiters:
            Log.error('invalid consumer ({}) specified for formatter', consumer)
            return None
        elif not data_type:
            Log.error('data does not contain the "DataType" key')
            return None
        elif data_type not in self.funcs:
            Log.error('invalid type ({}) specified for formatter', data['DataType'])
            return None

        #
        # We have a proper call, execute the formatter.
        #
        return self.funcs[data_type][consumer](data, consumer, self.delimiters[consumer])

# ----------------------------------------------------------------------------------------------------------------------

    def f_browser(self, data, consumer, delimiters):
        return self.f_human(data, consumer, delimiters)


    def f_human(self, data, consumer, delimiters):
        prefix, suffix, line_break = delimiters

        output  = ''
        output += line_break
        output += 'ZFM address  : {}{}'.format(data['ZFM'], line_break)
        output += 'Generated at : {}{}'.format(data['Timestamp'], line_break)
        output += line_break
        output += line_break

        header = '{:<20} {:<10} {:<21} {:<15} {:<15} {:<15}' + line_break
        layout = '{}{} {:<10} {:<21} {:<15} {:<15} {:<15}' + line_break

        output += header.format('Hostname', 'Type', 'IP address', 'Config state', 'Power state', 'Status/Health')
        output += header.format('-'*20, '-'*10, '-'*21, '-'*15, '-'*15, '-'*15)

        for name,node in data['Nodes'].items():
            node_type = node['Type']
            ip_address = node['Address']
            config_state = node['State']
            if config_state == 'Enabled':
                power_state = node['PowerState']
                status = '{}/{}'.format(node['Status']['State'], node['Status']['Health'])
            else:
                power_state = '--'
                status = '--/--'

            href = '<a href={}>{}</a>'.format(name, name) if consumer == 'BROWSER' else name
            filler = ' '*(20 - len(name))

            output += layout.format(href, filler, node_type, ip_address, config_state, power_state, status)

        return prefix + output + suffix


    def f_machine(self, data, consumer, delimiters):
        return json.dumps(data)

# ----------------------------------------------------------------------------------------------------------------------

    def n_browser(self, data, consumer, delimiters):
        return self.n_human(data, consumer, delimiters)


    def n_human(self, data, consumer, delimiters):
        prefix, suffix, line_break = delimiters

        output  = ''
        output += line_break
        output += 'ZFM address  : {}{}'.format(data['ZFM'], line_break)
        output += 'Generated at : {}{}'.format(data['Timestamp'], line_break)
        output += line_break
        output += line_break

        #
        # For enabled nodes, all the fields should be valid.
        #
        if data['ConfigState'] != 'Enabled':
            output += '{} is {}{}'.format(data['Hostname'], data['ConfigState'], line_break)
            return prefix + output + suffix

        #
        # For enabled nodes, all the fields should be valid.
        #
        output += ''
        output += 'Node name      {:<}{}'.format(data['Name'], line_break)
        output += 'Hostname       {:<}{}'.format(data['Hostname'], line_break)
        output += 'FQDN           {:<}{}'.format(data['FQDN'], line_break)
        output += line_break
        output += 'Config state   {:<}{}'.format(data['ConfigState'], line_break)
        output += 'Power state    {:<}{}'.format(data['ConfigState'], line_break)
        output += 'Status         {:<}{}'.format(data['Status'], line_break)
        output += line_break
        output += 'UID            0x{:<X}{}'.format(data['UID'], line_break)
        output += 'TopoID         {:<}{}'.format(data['TopoID'], line_break)
        output += 'GeoID          {:<}{}'.format(data['GeoID'], line_break)
        output += 'AsicID         {:<}{}'.format(data['AsicID'], line_break)
        output += line_break

        #
        # Loop over the ports to get the basic states.
        #
        header = '{:<4} {:<15}  {:<15}  {:<21}  {:<15}  {:<}' + line_break
        layout = '{}{} {:<15}  {:<15}  {:<21}  {:<15}  {:<}' + line_break

        output += header.format('', '', '', '', '', 'Remote Node')
        output += header.format('Port', 'Config state', 'Status/Health', 'Link state', 'Interface state', 'UID/Port #')
        output += header.format('-'*4, '-'*15, '-'*15, '-'*21, '-'*15, '-'*15)

        for index, port in sorted(data['Ports'].items()):
            href = '<a href={}/{}>{}</a>'.format(data['Name'], index, index) if consumer == 'BROWSER' else index
            filler = ' '*(4-len(str(index)))
            output += layout.format(href, filler, port['ConfigState'], port['Status'], port['LinkState'], port['InterfaceState'], port['Remote'])

        return prefix + output + suffix


    def n_machine(self, data, consumer, delimiters):
        return json.dumps(data)

# ----------------------------------------------------------------------------------------------------------------------

    def p_browser(self, data, consumer, delimiters):
        return self.p_human(data, consumer, delimiters)


    def p_human(self, data, consumer, delimiters):
        prefix, suffix, line_break = delimiters

        output  = ''
        output += line_break
        output += 'ZFM address  : {}{}'.format(data['ZFM'], line_break)
        output += 'Generated at : {}{}'.format(data['Timestamp'], line_break)
        output += line_break
        output += line_break

        #
        # For disabled ports, nothing is valid.
        #
        if data['ConfigState'] != 'Enabled':
            output += '{} port {} is {}{}'.format(data['Hostname'], data['Index'], data['ConfigState'], line_break)
            return prefix + output + suffix

        #
        # For enabled nodes, all the fields should be valid.
        #
        output += ''
        output += '{:<} port {}{}'.format(data['Hostname'], data['Index'], line_break)
        output += line_break
        output += '    Config State       {:<}{}'.format(data['ConfigState'], line_break)
        output += '    Status/Health      {:<}{}'.format(data['Status'], line_break)
        output += '    Link State         {:<}{}'.format(data['LinkState'], line_break)
        output += '    Interface State    {:<}{}'.format(data['InterfaceState'], line_break)
        output += '    Remote neighbor    {:<}{}'.format(data['Remote'], line_break)
        output += line_break
        output += line_break

        #
        # Format the metrics.
        #
        metrics = data.get('Metrics', None)
        if metrics:
            layout = '    {:<24}  {:>20}' + line_break

            output += 'Interface Statistics:' + line_break

            interface_metrics = metrics['Interface']
            for s in Metrics.interface_fields():
                output += layout.format(s, interface_metrics[s])

            output += line_break
            output += line_break
            output += line_break

            #
            # Header and value format for counters and bytes.
            #
            layout = '{:<12}  {:>20}     {:>20}     {:>20}     {:>20}     {:>20}' + line_break

            #
            # Port Requestor/Responder statistics.
            #
            request_metrics = metrics.get('Request', None)
            response_metrics = metrics.get('Response', None)

            if request_metrics and response_metrics:
                output += 'Requestor/Responder Interface Statistics:' + line_break
                output += line_break
                output += layout.format('', 'Xmit Count', 'Xmit Bytes', 'Recv Count', 'Recv Bytes', '')
                output += layout.format('Requests',
                                      request_metrics['XmitCount'],
                                      request_metrics['XmitBytes'],
                                      request_metrics['RecvCount'],
                                      request_metrics['RecvBytes'],
                                      '')
                output += layout.format('Responses',
                                      response_metrics['XmitCount'],
                                      response_metrics['XmitBytes'],
                                      response_metrics['RecvCount'],
                                      response_metrics['RecvBytes'],
                                      '')

                output += line_break
                output += line_break
                output += line_break

            #
            # Port VC statistics.
            #
            vc_metrics = metrics.get('VC0', None)
            if vc_metrics:
                output += 'Packet Relay Interface Statistics:' + line_break
                output += line_break
                output += layout.format('', 'Xmit Packets', 'Xmit Bytes', 'Recv Packets', 'Recv Bytes', 'Occupancy')

                for vc in range(16):
                    vc_key = 'VC{}'.format(vc)
                    output += layout.format(vc_key,
                                          metrics[vc_key]['XmitCount'],
                                          metrics[vc_key]['XmitBytes'],
                                          metrics[vc_key]['RecvCount'],
                                          metrics[vc_key]['RecvBytes'],
                                          metrics[vc_key]['Occupancy'])

        return prefix + output + suffix


    def p_machine(self, data, consumer, delimiters):
        return json.dumps(data)

# ----------------------------------------------------------------------------------------------------------------------

