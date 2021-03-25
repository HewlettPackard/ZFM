#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import sys
import copy
import json
import pprint

from km.routers.router import Router

PRETTY_PRINT_WIDTH = 220


# ======================================================================================================================

def pdump(title, data):
    pp = pprint.PrettyPrinter(indent=4, width=PRETTY_PRINT_WIDTH, compact=True)
    tab = '    ' if len(title) > 0 else ''

    print(title)
    for line in pp.pformat(data).splitlines(): print(tab, line)

# ======================================================================================================================

#
# hyperX specific hardware mappings.
#
def P(x):
    return [ i for i in range(6*x,6*x+6) ]


hw_mapping = { 1 : P( 0) + P( 2) + P( 3) + P( 6) + P( 7),
               2 : P( 1) + P( 4) + P( 5) + P( 8) + P( 9),
               3 : P(10) + P(12) + P(13) + P(16) + P(17),
               4 : P(11) + P(14) + P(15) + P(18) + P(19) }

ls_mapping = { index : key for index in range(120) for key,value in hw_mapping.items() if index in value }

# ======================================================================================================================

#
# hyperX architectural class.
#
class HyperX():

    def __init__(self, parameters):
        self.parameters = parameters

    # ------------------------------------------------------------------------------------------------------------------

    def process(self, nodes, connections, routing_config):

        #
        # Create the architectural specific representation of the fabric configuration.
        #
        self.fabric = Fabric(nodes, connections, self.parameters)

        #
        # Load the routers and apply them to the fabric.
        #
        for tc_name, tc_class in routing_config.items():
            router = Router(self.fabric, tc_name, tc_class)
            allnodes = self.fabric.apply_router(router)

        return allnodes

# ======================================================================================================================

#
#
#
class Fabric():
    def __init__(self, nodes, connections, parameters):
        self.allnodes = {}

        self.config = { 'Switches'   : {},
                        'Logicals'   : {},
                        'Nodes'      : {},
                        'Routes'     : {},
                        'GCIDs'      : set(),
                        'Parameters' : parameters,
                      }

        for node_parameters in nodes:
            self.create_node(node_parameters)

        for connection_parameters in connections:
            self.create_connection(connection_parameters)

        #
        # Build up the data structures from the configuration.
        #
        self.__split_switches__()
        self.__remap_links__()
        self.__configure_logicals__()
        self.__configure_nodes__()
        self.__gather_gcids__()

# ----------------------------------------------------------------------------------------------------------------------

    def create_node(self, parameters):
        name, model, topoid, geoid, gcids, constants = parameters

        #
        # Determine the number of ports.
        #
        if model == 'Switch':
            switch_range = constants['SWITCHES']
            port_range = constants['SWITCH_PORTS']
        elif model == 'Compute':
            switch_range = [0, 0]
            port_range = constants['FABRIC_ADAPTER_PORTS']
        elif model == 'IO':
            switch_range = [0, 0]
            port_range = constants['FABRIC_ADAPTER_PORTS']
        elif model == 'Memory':
            switch_range = [0, 0]
            port_range = constants['SWITCH_PORTS']

        num_ports = (1 + switch_range[1] - switch_range[0]) * (1 + port_range[1] - port_range[0])

        #
        # The actual node.
        #
        if model == 'Switch':
            self.config['Switches'][name] = self.create_switch_info(name, gcids, topoid, num_ports)
        else:
            self.config['Nodes'][name] = self.create_node_info(name, model, gcids, topoid, num_ports)


    def create_connection(self, parameters):
        src_name, src_port, dst_name, dst_port = parameters

        src_node = self.get_node_info(src_name)
        dst_node = self.get_node_info(dst_name)

        #
        # Verify the src node.
        #
        if not src_node                     : raise ValueError('unknown node named {}'.format(src_name))
        if src_port in src_node['Links']    : raise ValueError('{},{} already connected'.format(src_name, src_port))
        if src_port >= src_node['NumPorts'] : raise ValueError('{},{} port value too large'.format(src_name, src_port))

        #
        # Verify the dst node.
        #
        if not dst_node                     : raise ValueError('unknown node named {}'.format(dst_name))
        if dst_port in dst_node['Links']    : raise ValueError('{},{} already connected'.format(dst_name, dst_port))
        if dst_port >= dst_node['NumPorts'] : raise ValueError('{},{} port value too large'.format(dst_name, dst_port))

        #
        # Set the connections.
        #
        src_node['Links'][src_port] = (dst_name, dst_port)
        dst_node['Links'][dst_port] = (src_name, src_port)


    def create_switch_info(self, name, gcids, topoid, num_ports):
        plane, subnet = tuple(map(int, topoid.split('.')[0:2]))

        return { 'Model'       : 'Switch',
                 'Subnet'      : int(subnet),
                 'GCIDs'       : set(int(gcid,0) for gcid in gcids),
                 'TopoId'      : (plane, subnet),
                 'NumPorts'    : num_ports,
                 'Links'       : {}
               }


    def create_logical_info(self, ls_name, enabled_ports, plane, index, subnet, gcids):
        return { 'Base'        : ls_name.rsplit('.')[0],
                 'Name'        : ls_name,
                 'Model'       : 'Switch',
                 'Ports'       : { port : None for port in enabled_ports },
                 'L'           : set(),
                 'X'           : set(),
                 'Y'           : set(),
                 'GCIDs'       : set(gcids),
                 'Subnet'      : subnet,
                 'TopoId'      : (plane, index, subnet),
                 'Links'       : {},
                 'Connections' : {}
               }


    def create_node_info(self, name, model, gcids, topoid, num_ports):

        return { 'Name'        : name,
                 'Model'       : model,
                 'Links'       : {},
                 'Ports'       : {},
                 'L'           : set(),
                 'R'           : set(),
                 'GCIDs'       : set(int(gcid,0) for gcid in gcids),
                 'Subnet'      : int(topoid.split('.')[0]),
                 'TopoId'      : tuple(int(x) for x in topoid.split('.')),
                 'NumPorts'    : num_ports,
                 'Links'       : {},
                 'Connections' : {},
                 'SSDT'        : {},
                 'MSDT'        : {},
                 'REQ-VCAT'    : {},
                 'RSP-VCAT'    : {}
               }

    def create_port_info(self, port_type, remote_name, subnet):
        return { 'Type'  : port_type,
                 'Node'  : remote_name,
                 'Subnet': subnet,
                 'LPRT'  : {},
                 'MPRT'  : {},
                 'VCAT'  : {}
               }

# ----------------------------------------------------------------------------------------------------------------------

    def switch_to_logical_name(self, name, index):
        p_info = self.get_node_info(name)
        return '{}.{}'.format(name,index)


    def port_to_logical_name(self, name, port):
        p_info = self.get_node_info(name)
        return '{}.{}'.format(name,ls_mapping[port])

# ----------------------------------------------------------------------------------------------------------------------

    def get_switch_at(self, p, x, y):
        switch_topoid = (p, x, y)
        for ls_name,ls_node in self.config['Logicals'].items():
            if (ls_node['TopoId'] == switch_topoid):
                return ls_name


    def get_logicals(self):
        for ls_name,ls_info in self.config['Logicals'].items():
            yield (ls_name,ls_info)


    def get_logical_names(self):
        return set(ls_name for ls_name,_ in self.get_logicals())

# ----------------------------------------------------------------------------------------------------------------------

    def get_dimensions(self):
        return self.config['Parameters'].get('Dimensions', 2)


    def get_route_ports_between(self, src_name, dst_name, route_type):
        return self.config['Routes'][src_name][dst_name].get(route_type, set())

# ----------------------------------------------------------------------------------------------------------------------

    def get_node_info(self, name):
        for node_type in ['Logicals', 'Nodes', 'Switches']:
            info = self.config[node_type].get(name, None)
            if info:
                return info

        raise ValueError('unknown node named {}'.format(name))


    def get_nodes(self):
        for name,info in self.config['Nodes'].items():
            yield (name,info)


    def get_node_names(self):
        return set(name for name,_ in self.get_nodes())


    def get_model(self, name):
        node_info = self.get_node_info(name)
        return node_info['Model']


    def get_topoid(self, name):
        node_info = self.get_node_info(name)
        return node_info['TopoId']


    def get_subnet(self, name):
        node_info = self.get_node_info(name)
        return node_info['Subnet']

    def get_port_type(self, name, port):
        node_info = self.get_node_info(name)
        return node_info['Ports'][port]['Type']


    def get_ports(self, name):
        node_info = self.get_node_info(name)
        return set(node_info['Ports'].keys())


    def get_ports_typed(self, name, dim):
        node_info = self.get_node_info(name)
        return node_info[dim]


    def get_ports_between(self, src_name, dst_name):
        node_info = self.get_node_info(src_name)
        return node_info['Connections'].get(dst_name, set())


    def get_linked_names(self, node_name):
        node_info = self.get_node_info(node_name)
        return set(remote_data[0] for port,remote_data in node_info['Links'].items())

# ----------------------------------------------------------------------------------------------------------------------

    def get_connections(self, name):
        node_info = self.get_node_info(name)
        return node_info['Connections']


    def get_connected_names(self, name):
        node_info = self.get_node_info(name)
        return set(node_info['Connections'].keys())


    def get_connections_on_port(self, node_name, port):
        node_info = self.get_node_info(node_name)
        return set(remote_name for remote_name,local_ports in self.get_connections(node_name).items() if port in local_ports)

# ----------------------------------------------------------------------------------------------------------------------

    def get_gcids(self):
        return self.config['GCIDs']


    def get_gcids_for_name(self, name):
        node_info = self.get_node_info(name)
        return node_info['GCIDs']


    def get_gcids_for_subnet(self, gcids, subnet):
        return set([gcid for gcid in gcids if gcid >> 12 == subnet])


    def get_gcids_for_names(self, names):
        return set().union(*(self.get_gcids_for_name(name) for name in names))


    def get_gcids_from_node_port(self, node_name, local_port):
        local_names = self.get_connections_on_port(node_name, local_port)
        return self.get_gcids_for_names(local_names)


    def get_gcids_from_switch(self, ls_name):
        connected_names = set(name for name in self.get_connected_names(ls_name) if self.get_model(name) != 'Switch')
        return self.get_gcids_for_names(connected_names)


    def gcids_to_cids(self, gcids):
        return set(gcid & 0xfff for gcid in gcids)


    def gcids_to_sids(self, gcids):
        return set(gcid >> 12 for gcid in gcids)

# ----------------------------------------------------------------------------------------------------------------------

    def set_vcat_entry(self, vcat_table, vcats):
        for vc,vc_entry in vcats.items():
            vcat_table[vc] = vc_entry


    def set_VCAT(self, info, port, vcats):
        self.set_vcat_entry(info['Ports'][port]['VCAT'], vcats)


    def set_REQ_VCAT(self, info, vcats):
        self.set_vcat_entry(info['REQ-VCAT'], vcats)


    def set_RSP_VCAT(self, info, vcats):
        self.set_vcat_entry(info['RSP-VCAT'], vcats)

# ----------------------------------------------------------------------------------------------------------------------

    def set_routing_entry(self, table, out_port, xid, action, hopcount, mhc):
        entry = (action, hopcount, out_port)
        if xid not in table:
            table[xid] = { 'MHC' : mhc, 'Entries' : set() }
        table[xid]['Entries'].add(entry)


    def set_routing_table(self, table, out_ports, xids, action, hopcount, mhc):
        #
        # Loop over all ports and fill in the routing table.
        #
        for out_port in out_ports:
            for xid in xids:
                self.set_routing_entry(table, out_port, xid, action, hopcount, mhc)


    def set_LPRT(self, info, in_ports, out_ports, cids, action, hopcount, mhc):
        for in_port in in_ports:
            self.set_routing_table(info['Ports'][in_port]['LPRT'], out_ports - set([in_port]), cids, action, hopcount, mhc)


    def set_MPRT(self, info, in_ports, out_ports, sids, action, hopcount, mhc):
        for in_port in in_ports:
            self.set_routing_table(info['Ports'][in_port]['MPRT'], out_ports - set([in_port]), sids, action, hopcount, mhc)


    def set_SSDT(self, info, out_port, cids, action, hopcount, mhc):
        self.set_routing_table(info['SSDT'], out_port, cids, action, hopcount, mhc)


    def set_MSDT(self, info, out_port, sids, action, hopcount, mhc):
        self.set_routing_table(info['MSDT'], out_port, sids, action, hopcount, mhc)

# ----------------------------------------------------------------------------------------------------------------------

    def apply_node_vcat(self, router, node_name):
        node_info = self.get_node_info(node_name)
        node_vcats = router.get_node_vcat(node_name)

        self.set_REQ_VCAT(node_info, node_vcats['Request'])
        self.set_RSP_VCAT(node_info, node_vcats['Response'])

        for port_type in 'LR':
            ports = set(self.get_ports_typed(node_name, port_type))
            for port in ports:
                self.set_VCAT(node_info, port, node_vcats['Switch'])


    def apply_node_routes(self, router, node_name):
        node_info = self.get_node_info(node_name)
        action = router.get_action('X_DIRECT')
        hopcount = router.get_hopcount('X_DIRECT')
        node_routes = router.get_node_routes(self, node_name)

        #
        # SSDT
        #
        for port,gcids in node_routes['SSDT'].items():
            cids  = self.gcids_to_cids(gcids)
            self.set_SSDT(node_info, [port], cids, action, hopcount, 7)

        #
        # MSDT
        #
        for port,gcids in node_routes['MSDT'].items():
            sids  = self.gcids_to_sids(gcids)
            self.set_MSDT(node_info, [port], sids, action, hopcount, 7)

        #
        # LPRT
        #
        for port_pair, gcids in node_routes['LPRT'].items():
            in_port, out_port = port_pair

            if out_port != in_port:
                cids  = self.gcids_to_cids(gcids)
                self.set_LPRT(node_info, set([in_port]), set([out_port]), cids, action, hopcount, 7)

        #
        # MPRT
        #
        for port_pair, gcids in node_routes['MPRT'].items():
            in_port, out_port = port_pair

            if out_port != in_port:
                sids  = self.gcids_to_sids(gcids)
                self.set_MPRT(node_info, set([in_port]), set([out_port]), sids, action, hopcount, 7)

# ----------------------------------------------------------------------------------------------------------------------

    def apply_switch_vcat(self, router, ls_name):
        ls_info  = self.get_node_info(ls_name)
        ls_vcats = router.get_switch_vcat(ls_name)

        for port_type in 'LXY':
            in_ports = set(self.get_ports_typed(ls_name, port_type))
            for in_port in in_ports:
                self.set_VCAT(ls_info, in_port, ls_vcats[port_type])


    def apply_switch_routes(self, router, ls_name):
        ls_info   = self.get_node_info(ls_name)
        ls_ports  = self.get_ports(ls_name)

        ports = { port_type : set(self.get_ports_typed(ls_name, port_type)) for port_type in 'LXY' }

        #
        # Set routing table (LPRT) for exiting to local nodes.  This section of code processes the 'EXIT'
        # routing action.
        #
        route_type = 'EXIT'
        for out_port in ports['L']:
            names = self.get_connections_on_port(ls_name, out_port)
            gcids = self.get_gcids_for_names(names)
            cids  = self.gcids_to_cids(gcids)

            action = router.get_action(route_type)
            hopcount = router.get_hopcount(route_type)

            self.set_LPRT(ls_info, ls_ports, set([out_port]), cids, action, hopcount, 7)

        #
        # Set routing tables (LPRT, MPRT) to remote nodes.  This secionof code processes all of the
        # routing actions except 'EXIT'.
        #
        for dst_name,_ in self.get_logicals():
            routes = router.get_switch_to_switch_routes(self, ls_name, dst_name)
            if routes:
                dst_location = routes['Location']

                gcids = set(self.get_gcids_from_switch(dst_name))
                sids  = self.gcids_to_sids(gcids)
                cids  = self.gcids_to_cids(gcids)

                for port_type in 'LXY':
                    for route_type in router.get_routing_state(dst_location, port_type):
                        out_ports = routes['Paths'][route_type]
                        action = router.get_action(route_type)
                        hopcount = router.get_hopcount(route_type)

                        if route_type.startswith('X'):
                            self.set_LPRT(ls_info, ports[port_type], out_ports, cids, action, hopcount, 1)
                        elif route_type.startswith('Y'):
                            self.set_MPRT(ls_info, ports[port_type], out_ports, sids, action, hopcount, 2)

# ----------------------------------------------------------------------------------------------------------------------

    def apply_router(self, router):

        #
        # Route the core fabric.
        #
        for ls_name,_ in self.get_logicals():
            self.apply_switch_routes(router, ls_name)
            self.apply_switch_vcat(router, ls_name)

        #
        # Route the edge fabric.
        #
        for node_name,_ in self.get_nodes():
            self.apply_node_routes(router, node_name)
            self.apply_node_vcat(router, node_name)

        #
        # Merge the logicals back into single logicals.
        #
        for ls_name,ls_info in self.get_logicals():
            base_name = ls_info['Base']

            if base_name not in self.allnodes:
                self.allnodes[base_name] = { 'Ports' : {},
                                             'Links' : {},
                                             'GCIDs' : ls_info['GCIDs'],
                                             'Model' : ls_info['Model'] }

            self.allnodes[base_name]['Links'].update(ls_info['Links'])

            for port, port_info in ls_info['Ports'].items():
                self.allnodes[base_name]['Ports'][port] = ls_info['Ports'][port]

        #
        # Add the regular nodes into the list.
        #
        for node_name,_ in self.get_nodes():
            node_info = self.get_node_info(node_name)
            self.allnodes[node_name] = node_info

        return self.allnodes

# ----------------------------------------------------------------------------------------------------------------------

    #
    # Internal functions only.
    #

    #
    # Split the switches into logical switches.
    #
    def __split_switches__(self):
        switches = self.config['Switches']
        logicals = self.config['Logicals']

        for p_name,p_info in switches.items():
            gcids  = p_info['GCIDs']
            plane  = p_info['TopoId'][0]
            subnet = p_info['Subnet']
            switch_links = p_info['Links']
            enabled_ports = set(switch_links.keys())

            #
            # Split the switches into logical switches.
            #
            for index in range(1,4+1):
                ls_name = self.switch_to_logical_name(p_name, index)
                ls_ports = set(key for key,value in ls_mapping.items() if value == index)
                ls_enabled_ports = ls_ports & enabled_ports

                logicals[ls_name] = self.create_logical_info(ls_name, ls_enabled_ports, plane, index, subnet, gcids)
                logicals[ls_name]['Links'] = { port : switch_links[port] for port in ls_enabled_ports }


    def __remap_links__(self):
        logicals = self.config['Logicals']
        nodes    = self.config['Nodes']

        for node_name in self.get_logical_names() | self.get_node_names():
            node_info = self.get_node_info(node_name)

            #
            # Assign switch connections to the node.  Remap their names to the right logical switch name.
            #
            for port, remote_data in node_info['Links'].items():
                remote_name, remote_port = remote_data

                #
                # If the remote node is a switch, find the correct logical switch for it.
                #
                remote_model = self.get_model(remote_name)
                if remote_model == 'Switch':
                    remote_name = self.port_to_logical_name(remote_name, remote_port)
                    node_info['Links'][port] = (remote_name, remote_port)

                #
                # Add connections for the remote node.
                #
                node_info['Connections'].setdefault(remote_name, set()).add(port)


    def __configure_logicals__(self):
        logicals = self.config['Logicals']

        #
        # Add further away nodes to the connection list.  This will tell us the port to use to access a
        # node which is available via a non-switch node.  For example, <Logical> -> <IO> -> <Memory>.
        #
        ls_names = self.get_logical_names()

        for ls_name, ls_info in logicals.items():
            ls_connections = self.get_connected_names(ls_name) - ls_names

            while len(ls_connections) > 0:
                connection_name = ls_connections.pop()
                connection_ports = ls_info['Connections'][connection_name]

                remote_names = self.get_linked_names(connection_name) - self.get_connected_names(ls_name) - ls_names
                for remote_name in remote_names:
                    ls_info['Connections'].setdefault(remote_name, set()).update(connection_ports)
                    ls_connections.add(remote_name)

        #
        # We determine the type of each port (LOCAL, X, or Y).
        #
        for ls_name, ls_info in logicals.items():
            ls_subnet = self.get_subnet(ls_name)

            for port, remote_data in ls_info['Links'].items():
                remote_name,_ = remote_data
                remote_model = self.get_model(remote_name)
                remote_subnet = self.get_subnet(remote_name)

                if remote_model != 'Switch':                        # local node
                    port_type = 'L'
                elif remote_subnet == ls_subnet:                    # same subnet - X port
                    port_type = 'X'
                else:                                               # different subnets - Y port
                    port_type = 'Y'

                ls_info[port_type].add(port)
                ls_info['Ports'][port] = self.create_port_info(port_type, remote_name, ls_subnet)


    def __configure_nodes__(self):
        logicals = self.config['Logicals']

        #
        # The ports on a non-switch node can be of two types:
        #   R - remote port - connected to a switch node (used to access the rest of the fabric)
        #   L - local port  - connected to a non-switch node (only for access to connected node)
        #
        for node_name, node_info in self.get_nodes():
            node_model = self.get_model(node_name)

            for port,remote_data in node_info['Links'].items():
                remote_name,_ = remote_data
                remote_subnet = self.get_subnet(remote_name)

                if node_model == 'Memory':                          # everything is remote to a memory node
                    port_type = 'R'
                elif remote_name in logicals:                       # other end of the link is the fabric
                    port_type = 'R'
                else:                                               # locally connected nodes
                    port_type = 'L'

                node_info[port_type].add(port)
                node_info['Ports'][port] = self.create_port_info(port_type, remote_name, remote_subnet)


    #
    # Gather all of the GCIDs in the fabric.
    #
    def __gather_gcids__(self):
        self.config['GCIDs' ] = self.get_gcids_for_names(self.get_node_names())

