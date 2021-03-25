#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import os
import re
import sys
import copy
import json
import pprint


# ======================================================================================================================

PRETTY_PRINT_WIDTH = 220

def pdump(title, data):
    pp = pprint.PrettyPrinter(indent=4, width=PRETTY_PRINT_WIDTH, compact=True)
    tab = '    ' if len(title) > 0 else ''

    print(title)
    for line in pp.pformat(data).splitlines(): print(tab, line)

# ======================================================================================================================

#
# Small functions to decompose entries in the VC map.
#
def TC(tc_pc_rc_vc): return tc_pc_rc_vc[0]
def PC(tc_pc_rc_vc): return tc_pc_rc_vc[1]
def RC(tc_pc_rc_vc): return tc_pc_rc_vc[2]
def VC(tc_pc_rc_vc): return tc_pc_rc_vc[3]

# ======================================================================================================================

class NxM():


    def __init__(self, name, parameters, vc_map):
        self.action_types = {
            'X_DIRECT'  : 0,
            'X_DEROUTE' : 1,
            'X_FINISH'  : 2,
            'Y_DIRECT'  : 3,
            'Y_DEROUTE' : 4,
            'Y_FINISH'  : 5,
            'EXIT'      : 6,
            'INVALID'   : 7,
        }

        self.MAX_THRESHOLD = 7

        self.name = name
        self.vc_map = vc_map
        self.parameters = parameters

        #
        # Determine the ingress and egress RCs.
        #
        self.ingress_rc_type = self.parameters.get('IngressRC', 0)
        if type(self.ingress_rc_type) is str:
            if self.ingress_rc_type.isdigit():
                self.ingress_rc_type = int(self.ingress_rc_type)
            else:
                self.ingress_rc_type = 0

        self.egress_rc_type = self.parameters.get('EgressRC', -1)
        if type(self.egress_rc_type) is str:
            if self.egress_rc_type.isdigit():
                self.egress_rc_type = int(self.egress_rc_type)
            else:
                self.egress_rc_type = -1

        #
        # Setup the VCAT tables.
        #
        self.switch_vcat = self.setup_switch_vcat(vc_map)
        self.node_vcats = self.setup_node_vcats(vc_map)

# ----------------------------------------------------------------------------------------------------------------------

    def get_action(self, route_type):
        return self.action_types.get(route_type, self.action_types['INVALID'])


    def get_hopcount(self, route_type):
        return 1 if 'DEROUTE' in route_type else 0


    def get_node_vcat(self, name):
        return self.node_vcats


    def get_switch_vcat(self, name):
        return self.switch_vcat


    def routing_allowed(self, fabric, name):
        model = fabric.get_model(name)
        return model in self.parameters.get('NodeRouters', [])

# ----------------------------------------------------------------------------------------------------------------------

    #
    # This section contains the code to setup nodes.
    #
    def setup_node_vcats(self, vc_map):

        tc = set(TC(entry) for entry in vc_map).pop()
        pc_list = sorted(set(PC(entry) for entry in vc_map))
        vc_min = [ min(VC(entry) for entry in vc_map if PC(entry) == pc_list[i]) for i in range(len(pc_list)) ]
        vc_delta = vc_min[1] - vc_min[0]

        unused = (0,0) # Mask,Threshold
        node_vcats = { 'Switch' : {}, 'Request' : {} , 'Response' : {} }
        action = self.action_types['X_DIRECT']

        #
        # Setup a switch VCAT in case it is needed.
        #       Set vc[X_DIRECT] = pc_mask  - for LPRT and MPRT
        #
        threshold = self.MAX_THRESHOLD

        for pc in pc_list:
            pc_mask = sum(1 << VC(entry) for entry in vc_map if PC(entry) == pc)

            for entry in vc_map:
                if PC(entry) == pc:
                    vc = VC(entry)

                    node_vcats['Switch'][vc] = { action : copy.copy(unused) for action in range(8) }
                    node_vcats['Switch'][vc][action] = (pc_mask, threshold)

        #
        # Setup the REQ-VCAT.
        #       Set vc[X_DIRECT] = tc_mask - for LPRT
        #
        # The REQ-VCAT is indexed by the TC.  There is 1 TC per router.
        #
        pc = pc_list[0]
        tc_mask = sum(1 << VC(entry) for entry in vc_map if PC(entry) == pc)

        node_vcats['Request'][tc] = { action : copy.copy(unused) for action in range(8) }
        node_vcats['Request'][tc][action] = (tc_mask, threshold)

        #
        # Setup the RSP-VCAT.
        #       Set vc[X_DIRECT] = rc_mask - for LPRT
        #
        # The RSP-VCAT entries are setup in the VC rows which correspond to the REQ-VCAT entries.
        # Hence, we need to offset them in order for them to align correctly.  This also means
        # that the PCs must be identical in layout.
        #
        pc = pc_list[1]

        for entry in vc_map:
            if PC(entry) == pc:
                rc = RC(entry)
                vc = VC(entry)
                rc_mask = sum(1 << VC(x) for x in vc_map if RC(x) == rc)

                node_vcats['Response'][vc - vc_delta] = { action : copy.copy(unused) for action in range(8) }
                node_vcats['Response'][vc - vc_delta][action] = (rc_mask, threshold)

        return node_vcats


    def get_node_routes(self, fabric, node_name):
        node_subnet  = fabric.get_subnet(node_name)
        node_can_route = self.routing_allowed(fabric, node_name)


        local_ports  = set(fabric.get_ports_typed(node_name, 'L'))
        remote_ports = set(fabric.get_ports_typed(node_name, 'R'))
        all_ports    = local_ports | remote_ports

        local_names  = set().union(*[fabric.get_connections_on_port(node_name, port) for port in local_ports])

        my_gcids     = fabric.get_gcids_for_name(node_name)
        all_gcids    = fabric.get_gcids()
        local_gcids  = set().union(*[fabric.get_gcids_for_name(name) for name in local_names])
        remote_gcids = all_gcids - my_gcids - local_gcids
        subnet_gcids = fabric.get_gcids_for_subnet(remote_gcids, node_subnet)

        #
        # Setup SSDT.
        #
        ssdt = {}

        for port in remote_ports:
            ssdt[port] = subnet_gcids

        for port in local_ports:
            ssdt[port] = fabric.get_gcids_from_node_port(node_name, port)

        #
        # Setup MSDT.
        #
        msdt = {}

        for port in remote_ports:
            msdt[port] = remote_gcids - subnet_gcids

        #
        # Setup LPRT.
        #
        # Four different port loops:
        #   1) local  -> remote
        #   2) remote -> local
        #   3) remote -> remote (if routing is enabled)
        #   4) local  -> local (if routing is enabled)
        #
        lprt = {}

        for in_port in local_ports:
            for out_port in remote_ports:
                lprt[(in_port,out_port)] = subnet_gcids

        for in_port in remote_ports:
            for out_port in local_ports:
                lprt[(in_port,out_port)] = fabric.get_gcids_from_node_port(node_name, out_port)

        if node_can_route:
            for in_port in remote_ports:
                for out_port in remote_ports:
                    lprt[(in_port,out_port)] = subnet_gcids

            for in_port in local_ports:
                for out_port in local_ports:
                    lprt[(in_port,out_port)] = fabric.get_gcids_from_node_port(node_name, out_port)

        #
        # Setup MPRT.
        #
        # Two different port loops:
        #   1) local  -> remote
        #   2) remote -> remote (if routing is enabled)
        #
        mprt = {}

        for in_port in local_ports:
            for out_port in remote_ports:
                mprt[(in_port,out_port)] = remote_gcids - subnet_gcids

        if node_can_route:
            for in_port in remote_ports:
                for out_port in remote_ports:
                    mprt[(in_port,out_port)] = remote_gcids - subnet_gcids

        return { 'SSDT' : ssdt, 'MSDT': msdt, 'LPRT' : lprt, 'MPRT' : mprt }

# ----------------------------------------------------------------------------------------------------------------------

    #
    # This section contains the code to setup switches.
    #
    def setup_switch_vcat(self, vc_map):

        pc_list = sorted(set(PC(entry) for entry in vc_map))
        unused = (0,0) # Mask,Threshold

        #
        # Translate the state machine into an action table.
        #
        self.action_table = {}
        for loc_port,route_types in self.state_machine.items():
            self.action_table[loc_port] = {}

            for route_type, vc_list in route_types.items():
                for vc in vc_list:
                    self.action_table[loc_port].setdefault(vc, [])
                    self.action_table[loc_port][vc].append(route_type)

        #
        # Clear the VCAT
        #
        switch_vcat = {}
        for port_type in 'LXY':
            switch_vcat[port_type] = {}
            for entry in vc_map:
                switch_vcat[port_type][VC(entry)] = { action : copy.copy(unused) for action in range(8) }

        #
        # The protocol classes are examined in order.
        #
        for pc in pc_list:
            rc0 = min(RC(entry) for entry in vc_map if PC(entry) == pc)
            rcn = max(RC(entry) for entry in vc_map if PC(entry) == pc)

            #
            # Calculate the masks for this PC.
            #
            rc_mask = [ 0 for rc in range(rc0,rcn+1) ]
            for entry in vc_map:
                if PC(entry) == pc:
                    rc_mask[RC(entry) - rc0] |= 1 << VC(entry)

            rc_mask.append(0)               # fence to end the RC list
            rc_mask.append(sum(rc_mask))    # sum of all RCs for exit processing

            #
            # Loop over all of the actions and fill in the appropriate value.
            #
            for loc_type,vc_actions in self.action_table.items():
                location,port_type = loc_type

                for entry in vc_map:
                    rc = RC(entry) - rc0
                    vc = VC(entry)

                    if (PC(entry) != pc) or (rc not in vc_actions): continue

                    vc_row = switch_vcat[port_type][vc]

                    for route_type in vc_actions[rc]:
                        rc_action = self.action_types[route_type]
                        threshold = self.get_threshold(port_type, route_type, rc)
                        mask = self.get_mask(location, port_type, route_type, rc, rc_mask)

                        if vc_row[rc_action][0] == 0:
                            vc_row[rc_action] = (mask, threshold)
                        elif mask != vc_row[rc_action][0]:
                            raise ValueError('{} {} {} {} causes an contradiction'.format(self.name, loc_type, vc, route_type))

        return switch_vcat


    def get_switch_to_switch_routes(self, fabric, src_name, dst_name):
        #
        # No routing to ourself.
        #
        if dst_name == src_name: return {}

        #
        # Each routing algorithm has a state machine which details the possible actions for each state.
        #
        # The state machine is a dictionary with keys of the form (xy,ptype).
        #
        #       The 'xy' parameter is 2 characters (one for each dimension).  If the character is upper case,
        #       then the source and destination nodes are aligned in that dimension.  If the character is
        #       lower case, then the dimension is not aligned.
        #
        #       There are 4 possibilities for the location:
        #
        #                | X dimension | Y dimension |
        #           -----+-------------+-------------+
        #           'XY' |     aligned |     aligned |
        #           'Xy' |     aligned | not aligned |
        #           'xY' | not aligned |     aligned |
        #           'xy' | not aligned | not aligned |
        #           -----+-------------+-------------+
        #
        #       The ptype parameter characterizes the dimensionality of the port.  There are three
        #       possibilities:
        #
        #           'L' - local port - attached to a Compute or IO node.
        #           'X' - X dimension port
        #           'Y' - Y dimension port
        #
        # Example:
        #       ('xy', 'Y') : { 'X_DIRECT'  : [0,1],
        #                       'X_DEROUTE' : [0],
        #                       'Y_DIRECT'  : [0,1] }
        #
        #       For this combination, we have 3 possible actions we can apply:
        #           'X_DIRECT'  - minimal route to a switch to align the x-coordinate.
        #           'X_DEROUTE' - deroute in the x-dimension.
        #           'Y_DIRECT'  - minimal route to a switch to align the y-coordinate.
        #
        #       The values for each action tells us the ingress RCs for which this action is applicable.
        #       For the 'X_DIRECT' case, we can apply this action if the incoming packet arrived on RC0 or RC1.
        #
        sp,sx,sy = fabric.get_topoid(src_name)
        dp,dx,dy = fabric.get_topoid(dst_name)

        #
        # If there is no path between these two switches, then return an empty route list.
        #
        if dp != sp: return {}

        #
        # Find the position of src relative to dst.
        #
        if   (dx == sx) and (dy == sy): src_location = 'XY'  # X and Y aligned
        elif (dx == sx)               : src_location = 'Xy'  # X aligned
        elif                (dy == sy): src_location = 'xY'  # Y aligned
        else                          : src_location = 'xy'  # neither X nor Y aligned

        #
        # Find the node that is on the intersection of the horizontal and vertical dimensions
        # from the source and destination nodes.
        #
        x_host = fabric.get_switch_at(sp,dx,sy) if src_location[0] == 'x' else None
        y_host = fabric.get_switch_at(dp,sx,dy) if src_location[1] == 'y' else None

        #
        # Get the ports for each type.
        #
        x_ports   = fabric.get_ports_typed(src_name, 'X')
        y_ports   = fabric.get_ports_typed(src_name, 'Y')

        #
        # Get the path types for each port type.
        #
        l_route_types = self.state_machine.get((src_location, 'L'), {})
        x_route_types = self.state_machine.get((src_location, 'X'), {})
        y_route_types = self.state_machine.get((src_location, 'Y'), {})

        all_route_types = set(l_route_types) | set(x_route_types) | set(y_route_types)

        #
        # Get the paths for each dimension.
        #
        x_direct  = fabric.get_ports_between(src_name, x_host)
        x_deroute = set(x_ports) - x_direct
        x_finish  = x_direct
        x_routes  = { 'X_DIRECT' : x_direct, 'X_DEROUTE' : x_deroute, 'X_FINISH' : x_finish }

        y_direct  = fabric.get_ports_between(src_name, y_host)
        y_deroute = set(y_ports) - y_direct
        y_finish  = y_direct
        y_routes  = { 'Y_DIRECT' : y_direct, 'Y_DEROUTE' : y_deroute, 'Y_FINISH' : y_finish }

        all_routes = { **x_routes, **y_routes }

        #
        # Add the route types which we need for this (src,dst) combination.
        #
        paths = { route_type : all_routes[route_type] for route_type in all_route_types }

        routes = { 'L' : l_route_types,
                   'X' : x_route_types,
                   'Y' : y_route_types,
                   'Paths' : paths,
                   'Location' : src_location,
                 }

        return routes

# ----------------------------------------------------------------------------------------------------------------------
