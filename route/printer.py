#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import os
import sys
import json
import pprint


class Printer():
    def __init__(self, outfile, debug_flag):
        self.fd = open(outfile, 'w')
        self.debug = debug_flag
        self.rkey_enable = 3 # Set me to 1 to enable R-Key

        self.pp = pprint.PrettyPrinter(indent=4, width=200, compact=True)

    # ----------------------------------------------------------------------------------------------------------------------------

    def print_route_set(self, route_set):
        data = {}
        for e, entry in enumerate(route_set) :
            data[e] = { "Valid"            : True,
                        "VCAction"         : entry[0],
                        "HopCount"         : entry[1],
                        "EgressIdentifier" : entry[2],
                      }

        return data


    def print_route_table(self, table):
        data = {}
        for index, route_set in table.items():
            data[index] = { 'MinimumHopCount' : route_set['MHC'],
                            'RawEntryHex'     : "0x34EF124500000000",
                            'Entries'         : self.print_route_set(route_set['Entries'])
                          }

        return data


    def print_LPRT(self, lprt):
        return self.print_route_table(lprt)


    def print_MPRT(self, mprt):
        return self.print_route_table(mprt)


    def print_SSDT(self, ssdt):
        return self.print_route_table(ssdt)


    def print_MSDT(self, msdt):
        return self.print_route_table(msdt)

    # ----------------------------------------------------------------------------------------------------------------------------

    def print_vcat_row(self, row):
        data = {}
        for index in range(8):
            vcmask, threshold = row[index] if index in row else (0,0)
            data[index] = { 'Threshold' : threshold, 'VCMask' : vcmask }

        return data


    def print_vcat_table(self, table):

        data = {}
        for vc, row in table.items():
            data[vc] = self.print_vcat_row(row)

        return data


    def print_VCAT(self, vcat):
        return self.print_vcat_table(vcat)

    def print_REQ_VCAT(self, req_vcat):
        return self.print_vcat_table(req_vcat)

    def print_RSP_VCAT(self, rsp_vcat):
        return self.print_vcat_table(rsp_vcat)

    # ----------------------------------------------------------------------------------------------------------------------------

    def print_port(self, port_info):
        return { 'LPRT'      : self.print_LPRT(port_info['LPRT']),
                 'MPRT'      : self.print_MPRT(port_info['MPRT']),
                 'VCAT'      : self.print_VCAT(port_info['VCAT']),
                 'Registers' : None
               }

    def print_common(self, node_info):
        data = {}
        data['Registers'] = {}
        data['Constants'] = { 'Enabled' : list(node_info['Ports'].keys()), 'Model' : node_info['Model'], 'Rkey_Enable' : self.rkey_enable }
        data['Links'] = { port : (link_data[0].split('.')[0], link_data[1]) for port, link_data in node_info['Links'].items() }
        data['Ports'] = { port : self.print_port(port_info) for port,port_info in node_info['Ports'].items() }
        data['GCIDs'] = list(node_info['GCIDs'])

        return data

    # ----------------------------------------------------------------------------------------------------------------------------

    def print_Switch(self, node_info):
        return self.print_common(node_info)


    def print_Compute(self, node_info):
        data = self.print_common(node_info)

        data['SSDT'] = self.print_LPRT(node_info['SSDT'])
        data['MSDT'] = self.print_MSDT(node_info['MSDT'])
        data['REQ-VCAT'] =  self.print_REQ_VCAT(node_info['REQ-VCAT'])
        data['RSP-VCAT'] =  self.print_RSP_VCAT(node_info['RSP-VCAT'])

        return data


    def print_IO(self, node_info):
        return self.print_Compute(node_info)


    def print_Memory(self, node_info):
        data = self.print_common(node_info)

        data['SSDT'] = self.print_LPRT(node_info['SSDT'])
        data['MSDT'] = self.print_MSDT(node_info['MSDT'])
        data['REQ-VCAT'] =  self.print_REQ_VCAT(node_info['REQ-VCAT'])
        data['RSP-VCAT'] =  self.print_RSP_VCAT(node_info['RSP-VCAT'])

        return data

    # ----------------------------------------------------------------------------------------------------------------------------

    def print_data(self, nodes):

        data = {}

        for node_name, node_info in nodes.items():
            if node_info['Model'] == 'Switch'  : node_data = self.print_Switch(node_info)
            if node_info['Model'] == 'Compute' : node_data = self.print_Compute(node_info)
            if node_info['Model'] == 'IO'      : node_data = self.print_IO(node_info)
            if node_info['Model'] == 'Memory'  : node_data = self.print_Memory(node_info)

            data[node_name] = node_data

        if self.debug:
            self.pp.pprint(nodes)
        print(json.dumps(data, indent=4), file=self.fd)
