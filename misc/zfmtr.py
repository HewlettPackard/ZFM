#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#


import os
import sys
import json
import argparse
import pprint

lengths = [ 0 for i in range(6+1) ]
count = 0
total = 0
pp = pprint.PrettyPrinter(indent=4, width=90, compact=True)

path_length = -1

src_name  = None
src_ports = None
dst_name  = None
dst_ports = None
dst_gcid  = None
dst_sid   = None
dst_cid   = None


# ----------------------------------------------------------------------------------------------------------------------

#
# copied from routers/NxM.py
#
action_types = [ 'XM', 'XD', 'XF', 'YM', 'YD', 'YF', 'E', 'I', '' ]

def decode_path(path):

    name,port,_,_ = path[0]
    s = '{},{}'.format(name,port)

    for i in range(1,len(path)-1):
        name,port,action,egress = path[i]
        s += ' -> {},{} [{} {}]'.format(name, port, action_types[action], egress)

    name,port,_,_ = path[-1]
    s += ' -> {},{}'.format(name,port)

    return s

# ----------------------------------------------------------------------------------------------------------------------

def mask_to_vc(vcat, vc, action):
    mask = vcat[vc][str(action)]['VCMask']

    for i in range(16):
        if (mask & (1 << i)) != 0:
            return str(i)

    return None

# ----------------------------------------------------------------------------------------------------------------------

def ping(tmp_name, tmp_port, vc, path, depth):
    global count, lengths

    if (path_length >= 0) and (depth > path_length+2):
        return

    tmp_info = configuration[tmp_name]
    if (tmp_info['Constants']['Model'] != 'Switch'):
        if (tmp_name == dst_name):
            if tmp_port not in dst_ports:
                return

            if (path_length >= 0) and (depth != path_length+2):
                return

            gcids = tmp_info.get('GCIDs', [])
            if dst_gcid in gcids:
                count += 1
                final_path = path + [(tmp_name,tmp_port,-1,-1)]
                lengths[len(final_path) - 3] += 1
                if debug: print(decode_path(final_path))
                return
            else:
                print('error')
                sys.exit(0)
        elif (tmp_name != src_name):
            return

    tables = []
    if 'SSDT' in tmp_info:          # Start node only
        ssdt = tmp_info['SSDT']
        msdt = tmp_info['MSDT']
        if vc in tmp_info['REQ-VCAT']:
            vcat = tmp_info['REQ-VCAT']
        else:
            vcat = tmp_info['RSP-VCAT']

        if dst_cid in ssdt:
            tables.append(('SSDT',ssdt[dst_cid],vcat))
        elif dst_sid in msdt:
            tables.append(('MSDT',msdt[dst_sid],vcat))
        else:
            print('no start for path finding')
            sys.exit(0)
    else:
        if 'Ports' in tmp_info and tmp_port in tmp_info['Ports']:
            port_info = tmp_info['Ports'][tmp_port]
            if 'LPRT' in port_info:
                lprt = port_info['LPRT']
                mprt = port_info['MPRT']
                vcat = port_info['VCAT']
                if dst_cid in lprt: tables.append(('LPRT',lprt[dst_cid],vcat))
                if dst_sid in mprt: tables.append(('MPRT',mprt[dst_sid],vcat))


    links = tmp_info['Links']
    for table_name,xprt,vcat in tables:
        for index,entry in xprt['Entries'].items():
            action   = entry['VCAction']
            egress   = entry['EgressIdentifier']

            next_vc = mask_to_vc(vcat,vc,action)
            if next_vc:
                xid = dst_cid if table_name in ['LPTR','SSDT'] else dst_sid
                next_name, next_port = links[str(egress)]
                next_path = path + [(tmp_name,tmp_port,action,egress)]
                ping(next_name, str(next_port), next_vc, next_path, depth+1)

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    #
    # Get the command line parameters.
    #
    parser = argparse.ArgumentParser(description='fabric traceroute')

    parser.add_argument('-r', '--route',     help='route file',           required=True)
    parser.add_argument('-d', '--debug',     help='print routes',         required=False, default=False, action='store_true')
    parser.add_argument('-v', '--vc',        help='initial VC',           required=False, default='0')
    parser.add_argument('-l', '--length',    help='path length',          required=False)
    parser.add_argument('endpoints',         help='start and end nodes',  action='append', nargs=2, metavar='Endpoint')

    args = vars(parser.parse_args())
    vc = args['vc']
    debug = args['debug']
    routing_file = args['route']
    src_name, dst_name = args['endpoints'][0]

    if args['length']:
        path_length = int(args['length'])

    #
    # Read the routing file.
    #
    with open(routing_file) as f:
        configuration = json.load(f)

    #
    # Determine the source and destination endpoints.
    #
    src_name = args['endpoints'][0][0]
    if ',' in src_name:
        src_name,src_port = src_name.split(',')
        src_ports = [src_port]
    else:
        src_ports = sorted(configuration[src_name]['Links'].keys())

    dst_name = args['endpoints'][0][1]
    if ',' in dst_name:
        dst_name,dst_port = dst_name.split(',')
        dst_ports = [dst_port]
    else:
        dst_ports = sorted(configuration[dst_name]['Links'].keys())

    #
    # Setup the destination GCIDs.
    #
    dst_gcid = configuration[dst_name]['GCIDs'][0]
    dst_sid = str(dst_gcid >> 12)
    dst_cid = str(dst_gcid & 0xfff)

    #
    # Trace the route.
    #
    for port in src_ports:
        count = 0
        ping(src_name, port, vc, [], 0)
        print('{},{} -> {} has {} routes'.format(src_name, port, dst_name, count))
        total += count

    print()
    print('{} -> {} has {} routes'.format(src_name, dst_name, total))

    print()
    print('path lengths:', lengths)
