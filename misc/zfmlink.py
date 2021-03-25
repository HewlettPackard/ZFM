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

WIDTH  = 80
HEIGHT = 24

WHITE   = 7
BLACK   = 0
RED     = 1
GREEN   = 2
YELLOW  = 3
BLUE    = 4
MAGENTA = 5
CYAN    = 6


interface_fields = [
        "PCRCErrors",
        "ECRCErrors",
        "TXStompedECRC",
        "RXStompedECRC",
        "NonCRCTransientErrors",
        "LLRRecovery",
        "PacketDeadlineDiscards",
        "MarkedECN",
        "ReceivedECN",
        "LinkNTE",
        "AKEYViolations",

        "TotalTransReqs",
        "TotalTransReqBytes",
        "TotalRecvReqs",
        "TotalRecvReqBytes",
        "TotalTransResps",
        "TotalTransRespBytes",
        "TotalRecvResps",
        "TotalRecvRespBytes",
]

endpoint_help = textwrap.dedent("""\
    endpoint - node/port
               node = Gen-Z fabric manager process (MP) hostname or IP address
               port = Gen-Z interface port number""")

# -------------------------------------------------------------------------------------------------

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
    status,reply = rest(requests.get, url, None)
    return reply


def rest_patch(url, data):
    return rest(requests.patch, url, json.dumps(data))

# -------------------------------------------------------------------------------------------------

def portinfo_get(endpoints):

    for i in range(2):
        #
        # Get the chassis information.
        #
        url = 'http://{server}/redfish/v1/Chassis/1'.format(server=endpoints[i]['address'])
        chassis = rest_get(url)
        if chassis == None: return None

        #
        # Determine the attribute from the port number.
        #
        node_type = chassis['Oem']['Hpe']['NodeType']
        if node_type == 'Switch':
            endpoints[i]['attr'] = 'redfish/v1/Fabrics/GenZ/Switches/Switch{}/Ports/{}'.format(1 + endpoints[i]['port']//60, endpoints[i]['port']%60)
        elif node_type == 'Compute':
            endpoints[i]['attr'] = 'redfish/v1/Systems/1/FabricAdapters/1/Ports/{}'.format(endpoints[i]['port'])
        elif node_type == 'Memory':
            endpoints[i]['attr'] = 'redfish/v1/Fabrics/GenZ/Switches/Switch1/Ports/{}'.format(endpoints[i]['port'])
        elif node_type == 'IO':
            endpoints[i]['attr'] = 'redfish/v1/Systems/1/FabricAdapters/1/Ports/{}'.format(port_number)
        else:
            endpoints[i]['attr'] = None

    return all (endpoints[i]['attr'] for i in range(2))

# -------------------------------------------------------------------------------------------------

def statistics_reset(endpoints):

    interface_enabled  = { 'InterfaceState' : 'Enabled' }
    interface_disabled = { 'InterfaceState' : 'Disabled' }

    for i in range(2):
        url = 'http://{server}/{attribute}'.format(server=endpoints[i]['address'], attribute=endpoints[i]['attr'])
        status1, _ = rest_patch(url, interface_disabled)
        status2, _ = rest_patch(url, interface_enabled)

        if (status1//100) != 2 or (status2//100) != 2:
            return False

    return True


def statistics_get(endpoints):
    data = [None, None]

    for i in range(2):
        url = 'http://{server}/{attribute}/Metrics'.format(server=endpoints[i]['address'], attribute=endpoints[i]['attr'])
        data[i] = rest_get(url)

    return data

# -------------------------------------------------------------------------------------------------

def print_metrics(endpoints, metrics):

    i_metrics = [ metrics[0]['Gen-Z'], metrics[1]['Gen-Z'] ]

    #
    # Port information.
    #
    print()
    print()
    for i in range(2):
        print('Endpoint {}: {} port {} '.format(i+1, endpoints[i]['server'], endpoints[i]['port']))

    #
    # Interface errors.
    #
    print()
    print()
    print('Interface Statistics:')
    print()

    for t in interface_fields:
        print('     {:<26}  {:8}  {:8}'.format(t, i_metrics[0][t], i_metrics[1][t]))

    print()
    print()

# -------------------------------------------------------------------------------------------------

def display_metrics(stdscr, endpoints, metrics_curr, metrics_prev):

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

    for i in range(2):
        start_y += 1
        s = 'Endpoint {}: {} port {} '.format(i+1, endpoints[i]['server'], endpoints[i]['port'])
        stdscr.addstr(start_y, start_x, s, curses.color_pair(GREEN))

    #
    # Interface errors.
    #
    i_curr = [ metrics_curr[0]['Gen-Z'], metrics_curr[1]['Gen-Z'] ]
    i_prev = [ metrics_prev[0]['Gen-Z'], metrics_prev[1]['Gen-Z'] ]

    start_x  = 0
    start_y += 3
    stdscr.addstr(start_y, start_x, 'Interface Statistics:', curses.color_pair(GREEN))

    start_x  = 31
    stdscr.addstr(start_y,   start_x, 'Endpoint 1', curses.color_pair(GREEN))
    stdscr.addstr(start_y+1, start_x, '----------', curses.color_pair(GREEN))

    start_x  = 44
    stdscr.addstr(start_y,   start_x, 'Endpoint 2', curses.color_pair(GREEN))
    stdscr.addstr(start_y+1, start_x, '----------', curses.color_pair(GREEN))

    start_y += 1
    for t in interface_fields:
        start_x  = 5
        start_y += 1

        color = RED if any(i_curr[i][t] != i_prev[i][t] for i in range(2)) else WHITE
        s = '{:<26}'.format(t)
        stdscr.addstr(start_y, start_x, s, curses.color_pair(color))

        start_x = 31 - 14
        for i in range(2):
            start_x += 12
            color = RED if i_curr[i][t] != i_prev[i][t] else WHITE
            s = '{:12}'.format(i_curr[i][t])
            stdscr.addstr(start_y, start_x, s, curses.color_pair(color))

    #
    # Refresh the screen
    #
    stdscr.refresh()

# -------------------------------------------------------------------------------------------------

def draw_metrics(stdscr, endpoints, timer):

    metrics_curr = [None, None]
    metrics_prev = [None, None]

    #
    # Get the first set of stats.
    #
    metrics_curr = metrics_prev = statistics_get(endpoints)
    if any(metrics_curr[i] is None for i in range(2)):
        print('can\'t retrieve metrics from endpoints')
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
            metrics_curr = statistics_get(endpoints)
            display_metrics(stdscr, endpoints, metrics_curr, metrics_prev)
            metrics_prev = metrics_curr

            k = stdscr.getch()
            if chr(k) == 'r':
                statistics_reset(endpoints)
            elif chr(k) == 'q':
                return
        except ValueError:
            pass
        except KeyboardInterrupt:
            return

# -------------------------------------------------------------------------------------------------

def main(endpoints, timer, reset):

    #
    # Get the port attribute from the server
    #
    if not portinfo_get(endpoints):
        print('can\'t retrieve basic port information - check endpoints')
        return

    #
    # Do reset here and exit.
    #
    if reset:
        statistics_reset(endpoints)
        return

    #
    # If this is a one shot, just dump the stats.
    #
    if timer < 0:
        metrics_curr = statistics_get(endpoints)
        print_metrics(endpoints, metrics_curr)
        return

    #
    # Main loop
    #
    try:
        curses.wrapper(draw_metrics, endpoints, timer)
    except ValueError:
        print('screen is too small - it must be at least {}x{}'.format(WIDTH, HEIGHT))

# -------------------------------------------------------------------------------------------------

def usage():
    print('Link syntax is <ip_address>/<port_number>')
    sys.exit(0)


if __name__ == "__main__":
    #
    # Command defaults.
    #
    config_file = os.path.join(os.getcwd(), "fabric.conf")
    base_path = '/redfish/v1/'

    #
    # Get the command line parameters.
    #
    parser = argparse.ArgumentParser(description='link statistics', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-t', '--timer',  help='time between samples (seconds)',  type=int, default=-1)
    parser.add_argument('-r', '--reset',  help='reset port statistics',           action='store_true')
    parser.add_argument('endpoints',      help=endpoint_help,                     action='append', nargs=2, metavar='Endpoint')

    args = vars(parser.parse_args())

    #
    # Verify that the endpoints were specified correctly.
    #
    endpoints = {}
    for i, e in enumerate(args['endpoints'][0]):
        server, delimiter, port_number = e.partition('/')
        if not delimiter or not port_number:
            usage()

        server_address = resolve(server)
        endpoints[i] = { 'address' : server_address, 'server' : server, 'port' : int(port_number) }

    #
    # Args are good, call the main function.
    #
    main(endpoints, args['timer'], args['reset'])

