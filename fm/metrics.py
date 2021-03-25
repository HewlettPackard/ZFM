#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import os
import sys
import copy

from km.fm.log import Log

# ----------------------------------------------------------------------------------------------------------------------

class Metrics():

    def __init__(self, node, port, name):
        self.node = node
        self.port = port
        self.name = name
        self.data = None


    def get(self):
        return self.node.get(self.name)


    def patch(self, metrics_data):
        status,_ = self.node.patch(self.name, metrics_data)
        return status


    def reset(self):
        interface_enabled  = { 'InterfaceState' : 'Enabled' }
        interface_disabled = { 'InterfaceState' : 'Disabled' }

        status1,_ = self.node.patch(self.port.name, interface_disabled)
        status2,_ = self.node.patch(self.port.name, interface_enabled)

        return status1 and status2


    def check(self):

        #
        # Get the port metrics.
        #
        status, attr = self.get()
        if not status:
            Log.error('can\'t fetch port metrics for sweep of remote node')
            return status

        #
        # First time through.  Nothing to compare.
        #
        if not self.data:
            self.data = copy.deepcopy(attr)
            return True

        #
        # Check the error counters and flag those that are increasing.
        #
        for s in attr['Gen-Z']:
            v_curr =      attr['Gen-Z'][s]
            v_last = self.data['Gen-Z'][s]
            if v_curr != v_last:
                Log.error('{:<20} port {:<2} : {:<25} : {} -> {}', self.node.name, self.port.index, s, v_last, v_curr)

        self.data = copy.deepcopy(attr)
        return status

    @staticmethod
    def interface_fields():
        return [ 'PCRCErrors',
                 'ECRCErrors',
                 'TXStompedECRC',
                 'RXStompedECRC',
                 'NonCRCTransientErrors',
                 'LLRRecovery',
                 'PacketDeadlineDiscards',
                 'MarkedECN',
                 'ReceivedECN',
                 'LinkNTE',
                 'AKEYViolations',

                 'TotalTransReqs',
                 'TotalTransReqBytes',
                 'TotalRecvReqs',
                 'TotalRecvReqBytes',
                 'TotalTransResps',
                 'TotalTransRespBytes',
                 'TotalRecvResps',
                 'TotalRecvRespBytes',
        ]

# ----------------------------------------------------------------------------------------------------------------------
