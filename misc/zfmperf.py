#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import os
import sys
import time
import json
import socket
import textwrap
import argparse
import requests
import curses

from http import HTTPStatus

WIDTH  = 130
HEIGHT =  46

WHITE   = 7
BLACK   = 0
RED     = 1
GREEN   = 2
YELLOW  = 3
BLUE    = 4
MAGENTA = 5
CYAN    = 6

interface_enabled  = { 'InterfaceState' : 'Enabled' }
interface_disabled = { 'InterfaceState' : 'Disabled' }

interface_fields = [ 'PCRCErrors',
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
                     'TotalRecvRespBytes', ]

args = {}

endpoint_help = textwrap.dedent("""\
    endpoint - node/port
               node = Gen-Z fabric manager process (MP) hostname or IP address
               port = Gen-Z interface port number""")

# ----------------------------------------------------------------------------------------------------------------------

def rest(f, url, data):
    REST_RETRIES = 3
    headers = { "Accept": "application/json", "Content-Type": "application/json" }

    r = None
    reply = None

    retries = 0
    status = HTTPStatus.REQUEST_TIMEOUT
    while (retries < REST_RETRIES) and (status == HTTPStatus.REQUEST_TIMEOUT):
        retries += 1

        try:
            r = f(url, headers=headers, data=data)
        except requests.exceptions.Timeout as e:
            status = HTTPStatus.REQUEST_TIMEOUT
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
        except requests.exceptions.ConnectionError as e:
            status = HTTPStatus.SERVICE_UNAVAILABLE
        except requests.exceptions.RequestException as e:
            status = e.response.status_code
        except:
            status = HTTPStatus.BAD_REQUEST
        else:
            status = r.status_code

    if r and status//100 == 2:
        if r.text and len(r.text) > 0:
            reply = r.text
            if reply and reply.startswith('<pre>'): reply = reply[5:-6]
            reply = json.loads(reply)

    return status, reply

# ----------------------------------------------------------------------------------------------------------------------

def rest_get(url):
    return rest(requests.get, url, None)


def rest_patch(url, data):
    return rest(requests.patch, url, json.dumps(data))

# ----------------------------------------------------------------------------------------------------------------------

def portinfo_get(node, port_number):

    #
    # Get the chassis information.
    #
    url = 'http://{node}/redfish/v1/Chassis/1'.format(node=node)
    status, chassis = rest_get(url)
    if chassis == None: return None, None

    #
    # Determne the attribute from the port number.
    #
    node_type = chassis['Oem']['Hpe']['NodeType']
    if node_type == 'Switch':
        port_attribute = 'redfish/v1/Fabrics/GenZ/Switches/Switch{}/Ports/{}'.format(1 + port_number//60, port_number%60)
    elif node_type == 'Compute':
        port_attribute = 'redfish/v1/Systems/1/FabricAdapters/1/Ports/{}'.format(port_number)
    elif node_type == 'Memory':
        port_attribute = 'redfish/v1/Fabrics/GenZ/Switches/Switch1/Ports/{}'.format(port_number)
    elif node_type == 'IO':
        port_attribute = 'redfish/v1/Systems/1/FabricAdapters/1/Ports/{}'.format(port_number)

    #
    # Find the ports neighbor.
    #
    url = 'http://{node}/{attribute}'.format(node=node, attribute=port_attribute)
    status, port_info = rest_get(url)
    if not port_info: return None, None

    neighbor = port_info['Oem']['Hpe']['RemoteComponentID']
    if neighbor['UID'] != 0:
        neighbor_id = 'Neighbor: 0x{:08X}/{}'.format(neighbor['UID'], neighbor['Port'])
    else:
        neighbor_id = 'No neighbor'

    return port_attribute, neighbor_id

# ----------------------------------------------------------------------------------------------------------------------

def statistics_reset(node, attr):
    url = 'http://{node}/{attribute}'.format(node=node, attribute=attr)
    status1, _ = rest_patch(url, interface_disabled)
    status2, _ = rest_patch(url, interface_enabled)
    return (status1/100 == 2) and (status2/100 == 2)


def statistics_get(node, attr):
    url = 'http://{node}/{attribute}/Metrics'.format(node=node, attribute=attr)
    status, data = rest_get(url)
    return data

# ----------------------------------------------------------------------------------------------------------------------

def json_metrics(node, attr, header):

    metrics = statistics_get(node, attr)
    print(json.dumps(metrics))


def print_metrics(node, attr, header):

    layout1 = '     {:<10}  {:>20}  {:>20}  {:>20}  {:>20}'
    layout2 = '     {:<10}  {:>20}  {:>20}  {:>20}  {:>20}  {:>20}'

    metrics = statistics_get(node, attr)
    i_metrics = metrics['Gen-Z']

    #
    # Port information.
    #
    print()
    print()
    print(header)

    #
    # Interface errors.
    #
    print()
    print()
    print('Interface Statistics:')
    print()

    for s in interface_fields:
        print('     {:<26}  {:8}'.format(s, i_metrics[s]))

    #
    # Request/response counts.
    #
    try:
        x = metrics['Oem']['Hpe']['Metrics']['Request']
        x = metrics['Oem']['Hpe']['Metrics']['Response']

        print()
        print()
        print('Requestor/Responder Interface Statistics:')
        print()
        print(layout1.format('', 'Xmit Count', 'Xmit Bytes', 'Recv Count', 'Recv Bytes'))
        print(layout1.format('', '-'*20, '-'*20, '-'*20, '-'*20))

        for n in ['Request', 'Response']:
            r_metrics = metrics['Oem']['Hpe']['Metrics'][n]
            print(layout1.format(n,
                                r_metrics['XmitCount'],
                                r_metrics['XmitBytes'],
                                r_metrics['RecvCount'],
                                r_metrics['RecvBytes']))
    except:
        pass

    #
    # VC counts.
    #
    try:
        x = metrics['Oem']['Hpe']['Metrics']['VC0']

        print()
        print()
        print('Packet Relay Interface Statistics:')
        print()
        print(layout2.format('', 'Xmit Packets', 'Xmit Bytes', 'Recv Packets', 'Recv Bytes', 'Occupancy'))
        print(layout2.format('', '-'*20, '-'*20, '-'*20, '-'*20, '-'*20))

        for i in range(16):
            name = 'VC{}'.format(i)
            vc_metrics = metrics['Oem']['Hpe']['Metrics'][name]
            print(layout2.format(name,
                                vc_metrics['XmitCount'],
                                vc_metrics['XmitBytes'],
                                vc_metrics['RecvCount'],
                                vc_metrics['RecvBytes'],
                                vc_metrics['Occupancy']))
    except:
        pass

        print()
        print()


def display_metrics(stdscr, node, attr, header, metrics_curr, metrics_prev):

    layout1 = '{:<10}  {:>20}  {:>20}  {:>20}  {:>20}'
    layout2 = '{:<10}  {:>20}  {:>20}  {:>20}  {:>20}  {:>20}'

    #
    # Clear and refresh the screen for a blank canvas
    #
    stdscr.clear()
    stdscr.refresh()

    #
    # Port info.
    #
    start_x = 0
    start_y = 2
    stdscr.addstr(start_y, start_x, header, curses.color_pair(GREEN))

    #
    # Interface errors.
    #
    i_curr = metrics_curr['Gen-Z']
    i_prev = metrics_prev['Gen-Z']

    start_x  = 0
    start_y += 2
    stdscr.addstr(start_y, start_x, 'Interface Statistics:', curses.color_pair(GREEN))

    start_x  = 5
    start_y += 1
    for f in interface_fields:
        start_y += 1
        color = RED if i_prev[f] != i_curr[f] else WHITE
        s = '{:<26}  {:8}'.format(f, i_curr[f])
        stdscr.addstr(start_y, start_x, s, curses.color_pair(color))


    #
    # Request counts.
    #
    try:
        req_curr = metrics_curr['Oem']['Hpe']['Metrics']['Request']
        req_prev = metrics_prev['Oem']['Hpe']['Metrics']['Request']

        start_x  = 0
        start_y += 2
        stdscr.addstr(start_y, start_x, 'Requestor/Responder Interface Statistics:', curses.color_pair(GREEN))

        start_x  = 5
        start_y += 2
        s = layout1.format('', 'Xmit Count', 'Xmit Bytes', 'Recv Count', 'Recv Bytes')
        stdscr.addstr(start_y, start_x, s, curses.color_pair(WHITE))

        start_y += 1
        s = layout1.format('', '-'*20, '-'*20, '-'*20, '-'*20)
        stdscr.addstr(start_y, start_x, s, curses.color_pair(WHITE))

        start_y += 1
        color = GREEN if any(req_curr[n] != req_prev[n] for n in ['XmitCount', 'XmitBytes', 'RecvCount', 'RecvBytes']) else WHITE
        s = '{:<10}'.format('Requests')
        stdscr.addstr(start_y, start_x, s, curses.color_pair(color))
        start_x += 12
        for n in ['XmitCount', 'XmitBytes', 'RecvCount', 'RecvBytes']:
            color = GREEN if req_curr[n] != req_prev[n] else WHITE
            s = '{:20}'.format(req_curr[n])
            stdscr.addstr(start_y, start_x, s, curses.color_pair(color))
            start_x += 22
    except:
        pass

    #
    # Response counts.
    #
    try:
        rsp_curr = metrics_curr['Oem']['Hpe']['Metrics']['Response']
        rsp_prev = metrics_prev['Oem']['Hpe']['Metrics']['Response']

        start_x  = 5
        start_y += 1
        color = GREEN if any(rsp_curr[n] != rsp_prev[n] for n in ['XmitCount', 'XmitBytes', 'RecvCount', 'RecvBytes']) else WHITE
        s = '{:<10}'.format('Responses')
        stdscr.addstr(start_y, start_x, s, curses.color_pair(color))
        start_x += 12
        for n in ['XmitCount', 'XmitBytes', 'RecvCount', 'RecvBytes']:
            color = GREEN if rsp_curr[n] != rsp_prev[n] else WHITE
            s = '{:20}'.format(rsp_curr[n])
            stdscr.addstr(start_y, start_x, s, curses.color_pair(color))
            start_x += 22
    except:
        pass

    #
    # VC counts.
    #
    try:
        vc_curr = metrics_curr['Oem']['Hpe']['Metrics']['VC0']

        start_x  = 0
        start_y += 2
        stdscr.addstr(start_y, start_x, 'Packet Relay Interface Statistics:', curses.color_pair(GREEN))

        start_x  = 5
        start_y += 2
        s = layout2.format('', 'Xmit Packets', 'Xmit Bytes', 'Recv Packets', 'Recv Bytes', 'Occupancy')
        stdscr.addstr(start_y, start_x, s, curses.color_pair(WHITE))

        start_y += 1
        s = layout2.format('', '-'*20, '-'*20, '-'*20, '-'*20, '-'*20)
        stdscr.addstr(start_y, start_x, s, curses.color_pair(WHITE))

        for i in range(16):
            name = 'VC{}'.format(i)

            vc_curr = metrics_curr['Oem']['Hpe']['Metrics'][name]
            vc_prev = metrics_prev['Oem']['Hpe']['Metrics'][name]

            start_x  = 5
            start_y += 1
            color = GREEN if sum(vc_curr[i] - vc_prev[i] for i in vc_curr) > 0 else WHITE
            s = name
            stdscr.addstr(start_y, start_x, s, curses.color_pair(color))
            start_x += 12
            for n in ['XmitCount', 'XmitBytes', 'RecvCount', 'RecvBytes', 'Occupancy']:
                color = GREEN if vc_curr[n] != vc_prev[n] else WHITE
                s = '{:20}'.format(vc_curr[n])
                stdscr.addstr(start_y, start_x, s, curses.color_pair(color))
                start_x += 22
    except:
        pass

    #
    # Refresh the screen
    #
    stdscr.refresh()


def draw_metrics(stdscr, node_address, node, attr, header, timer):

    #
    # Get the first set of stats.
    #
    metrics_curr = metrics_prev = statistics_get(node_address, attr)
    if not metrics_curr:
        print('can\'t retrieve metrics from {}/{}'.format(node, args['attr']))
        return

    #
    # Start colors in curses
    #
    curses.start_color()
    curses.use_default_colors()
    for i in range(0,curses.COLORS):
        curses.init_pair(i, i, -1)

    curses.curs_set(0)

    #
    # Initialization
    #
    stdscr.clear()
    stdscr.bkgd(' ', curses.color_pair(BLACK))
    height, width = stdscr.getmaxyx()
    if (width < WIDTH) or (height < HEIGHT):
        raise ValueError

    #
    # Loop forever
    #
    stdscr.timeout(1000*timer)
    while True:
        try:
            metrics_curr = statistics_get(node_address, attr)
            display_metrics(stdscr, node_address, attr, header, metrics_curr, metrics_prev)
            metrics_prev = metrics_curr

            k = stdscr.getch()
            if chr(k) == 'r':
                statistics_reset(node_address, attr)
            elif chr(k) == 'q':
                return
        except ValueError:
            pass
        except KeyboardInterrupt:
            return

# ----------------------------------------------------------------------------------------------------------------------

def resolve(hostname):

    if ':' in hostname:
        hostname, hostport = hostname.split(':')
    else:
        hostport = '8081'

    try:
        hostname = socket.gethostbyname(hostname)
    except:
        print('can\'t resolve the node address')
        sys.exit(0)

    return '{}:{}'.format(hostname, hostport)


def main(args):

    node,delimiter,port_number = args['endpoint'].partition('/')
    if not port_number:
        print('node/port is incorrectly specified')
        return

    timer = args['timer']
    reset = args['reset']
    json = args['json']

    node_address = resolve(node)

    #
    # Get the port attribute from the node
    #
    attr, neighbor_id = portinfo_get(node_address, int(port_number))
    if not attr:
        print('can\'t retrieve basic port information - check node address and port number')
        return

    #
    # Create the header.
    #
    header = '{}/{}    {}'.format(node, port_number, neighbor_id)

    #
    # Do reset here and exit.
    #
    if reset:
        statistics_reset(node_address, attr)
        return

    #
    # Do the one shot if no timer value specified.
    #
    if timer < 0:
        if not json:
            print_metrics(node_address, attr, header)
        else:
            json_metrics(node_address, attr, header)
        return

    #
    # Main loop
    #
    try:
        curses.wrapper(draw_metrics, node_address, node, attr, header, timer)
    except ValueError:
        print('screen is too small - it must be at least {}x{}'.format(WIDTH, HEIGHT))

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    #
    # Command defaults.
    #
    config_file = os.path.join(os.getcwd(), "fabric.conf")
    base_path = '/redfish/v1/'

    #
    # Get the command line parameters.
    #
    parser = argparse.ArgumentParser(description='performance monitor', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-o', '--output',  help='output file')
    parser.add_argument('-t', '--timer',   help='time between samples (seconds)',                  type=int, default=-1)
    parser.add_argument('-j', '--json',    help='output formatted as JSON',       required=False,  action='store_true')
    parser.add_argument('-r', '--reset',   help='reset port statistics',                           action='store_true')
    parser.add_argument('endpoint',        help=endpoint_help,                                     metavar='Endpoint')

    args = vars(parser.parse_args())

    #
    # Verify args.
    #
    if args['timer'] != -1 and args['json']:
        print('-t and -j are mutually exclusive')
        sys.exit(0)

    #
    # If the user specified an output file, then redirect to it.
    #
    if args['output']:
        try:
            fd = open(args['output'],'w')
            sys.stdout = fd
        except:
            print('can\'t open output file {}'.format(args['output']))
            sys.exit(0)

    main(args)

