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
import html
import socket
import textwrap
import argparse
import requests

from http import HTTPStatus

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


command_choices = [ 'up', 'down', 'reset', 'metrics', 'query' ]

endpoint_help = textwrap.dedent("""\
    endpoint - node/port
               node = Gen-Z fabric manager process (MP) hostname or IP address
               port = Gen-Z interface port number""")

command_help = textwrap.dedent("""\
    up      - bring the port to the Enabled State
    down    - bring the port to the Disabled State
    reset   - bring the port down and then up
    metrics - clear the metrics
    query   - dump port information """)

# -------------------------------------------------------------------------------------------------

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

    if not r:
        print('REST request failed with code {}'.format(status))
    elif status//100 != 2:
        print('REST request returned error code {}'.format(status))
    elif r.text and len(r.text) > 0:
        reply = r.text
        if reply and reply.startswith('<pre>'): reply = reply[5:-6]
        reply = json.loads(reply)

    return status//100 == 2, reply

# -------------------------------------------------------------------------------------------------

def rest_get(server, attribute):
    if attribute[0] == '/': attribute = attribute[1:]
    url = 'http://{server}/{attribute}'.format(server=server, attribute=attribute)
    return rest(requests.get, url, None)


def rest_patch(server, attribute, values):
    if attribute[0] == '/': attribute = attribute[1:]
    url = 'http://{server}/{attribute}'.format(server=server, attribute=attribute)
    data = json.dumps(values)
    return rest(requests.patch, url, data)

# ----------------------------------------------------------------------------------------------------------------------

def check_values(data, values):
    #
    # Traverse the local data struct and replace the appropriate element with new entries.
    #
    if values:
        for key in values:
            if type(data[key]) is dict and type(values[key]) is dict:
                if not check_values(data[key], values[key]):
                    return False
            elif data[key] != values[key]:
                return False

    return True


def wait_for(server, attribute, values, retries):
    port_ready = False

    while not port_ready and retries >= 0:
        retries -= 1
        time.sleep(1)
        status, data = rest_get(server, attribute)
        if not status:
            return False
        port_ready = check_values(data, values)

    return port_ready

# ----------------------------------------------------------------------------------------------------------------------

def port_metrics(args, attribute):
    server = args['server']

    interface_enabled  = { 'InterfaceState' : 'Enabled' }
    interface_disabled = { 'InterfaceState' : 'Disabled' }

    #
    # Clear the port metrics.  We do this by disabling and then enabling the interface.
    #
    status1, _ = rest_patch(server, attribute, interface_disabled)
    status2, _ = rest_patch(server, attribute, interface_enabled)
    return status1 and status2

# ----------------------------------------------------------------------------------------------------------------------

def port_reset(args, attribute):
    if not port_down(args, attribute):
        return False
    elif not port_up(args, attribute):
        return False
    else:
        return True

# ----------------------------------------------------------------------------------------------------------------------

def port_up(args, attribute):
    endpoint = args['endpoint']
    server = args['server']
    force = args['force']

    #
    # Fetch the port attribute.
    #
    status, data = rest_get(server, attribute)
    if not status:
        print('can\'t get the attribute for {}'.format(endpoint))
        sys.exit(1)

    port_state = data['Status']['State']
    port_health = data['Status']['Health']
    link_state = data['LinkState']
    if_state = data['InterfaceState']

    #
    # Validate the state before proceeding.
    #
    if port_state != 'Disabled' or port_health != 'OK' or link_state != 'Disabled' or if_state != 'Disabled':
        if not force:
            print('{} is not in a proper state for bringing up'.format(endpoint))
            print('            Status = {}/{}'.format(port_state, port_health))
            print('         LinkState = {}'.format(link_state))
            print('    InterfaceState = {}'.format(if_state))
            return False

        #
        # Force the interface down.
        #
        if not port_down(args, attribute):
            return False

    #
    # Start training.
    #
    values = { 'LinkState' : 'Enabled' }
    status, _ = rest_patch(server, attribute, values)
    if not status:
        print('{} PATCH of LinkState failed'.format(endpoint))
        return False

    #
    # Wait for training to complete.
    #
    if not wait_for(server, attribute, {'Status' : { 'State' : 'StandbyOffline', 'Health' : 'OK' }}, 5):
        print('{} did not transition to StandbyOffline'.format(endpoint))
        return False

    #
    # Set the interface state to enabled.
    #
    values = { 'InterfaceState' : 'Enabled' }
    status, _ = rest_patch(server, attribute, values)
    if not status:
        print('{} PATCH of InterfaceState failed'.format(endpoint))
        return False

    #
    # Wait for the interface to come ready.
    #
    if not wait_for(server, attribute, {'InterfaceState' : 'Enabled' }, 5):
        print('{} did not transition to Enabled'.format(endpoint))

    return True

# ----------------------------------------------------------------------------------------------------------------------

def port_down(args, attribute):
    endpoint = args['endpoint']
    server = args['server']
    force = args['force']

    #
    # Fetch the port attribute.
    #
    status, data = rest_get(server, attribute)
    if not data:
        print('can\'t get the attribute for {}'.format(endpoint))
        sys.exit(1)

    port_state = data['Status']['State']
    port_health = data['Status']['Health']
    link_state = data['LinkState']
    if_state = data['InterfaceState']

    #
    # Validate the state before proceeding.
    #
    if port_state not in ['StandbyOffline', 'Enabled'] or port_health != 'OK' or link_state != 'Enabled' or if_state != 'Enabled':
        if not force:
            print('{} is not in a proper state for bringing down'.format(endpoint))
            print('            Status = {}/{}'.format(port_state, port_health))
            print('         LinkState = {}'.format(link_state))
            print('    InterfaceState = {}'.format(if_state))
            return False

    #
    # Reset the port
    #
    values = { 'LinkState' : 'Disabled', 'InterfaceState' : 'Disabled' }
    status, _ = rest_patch(server, attribute, values)
    if not status:
        print('{} PATCH failed'.format(endpoint))
        return False

    #
    # Wait for the port state change to take affect.
    #
    if not wait_for(server, attribute, values, 5):
        print('{} did not transisiton to Disabled'.format(endpoint))
        return False

    #
    # Reset the state
    #
    values = { 'Status' : { 'State' : 'Disabled', 'Health' : 'OK' }}
    status, _ = rest_patch(server, attribute, values)
    if not status:
        print('{} PATCH failed'.format(endpoint))
        return False

    #
    # Wait for the port state change to take affect.
    #
    if not wait_for(server, attribute, values, 5):
        print('{} did not transition to Disabled'.format(endpoint))
        return False

    return True

# ----------------------------------------------------------------------------------------------------------------------

def port_query(args, attribute):
    endpoint = args['endpoint']
    server = args['server']

    #
    # Get the port attribute.
    #
    status, port_data = rest_get(server, attribute)
    if not status:
        print('{} GET failed'.format(endpoint))
        return False

    metrics_attribute = port_data['Metrics']['@odata.id']
    metrics_attribute = html.unescape(metrics_attribute)
    metrics_attribute = re.sub('<[^>]*>', '', metrics_attribute)

    #
    # Get the metrics attribute.
    #
    status, metrics_data = rest_get(server, metrics_attribute)
    if not status:
        print('{} GET failed'.format(endpoint))
        return False

    oem_data = port_data['Oem']['Hpe']
    oem_metrics = metrics_data['Oem']['Hpe']['Metrics']

    #
    # For enabled nodes, all the fields should be valid.
    #
    print()
    print('{}:'.format(endpoint))
    print()
    print('    State/Health       {}/{}'.format(port_data['Status']['State'], port_data['Status']['Health']))
    print('    Link State         {}'.format(port_data['LinkState']))
    print('    Interface State    {}'.format(port_data['InterfaceState']))
    print('    Remote neighbor    0x{:08X}/{}'.format(oem_data['RemoteComponentID']['UID'], oem_data['RemoteComponentID']['Port']))
    print()
    print()

    #
    # Format the metrics.
    #
    layout = '    {:<24}  {:>20}'

    print('Interface Statistics:')

    interface_metrics = metrics_data['Gen-Z']
    for s in interface_fields:
        print(layout.format(s, interface_metrics[s]))

    print()
    print()
    print()

    #
    # Header and value format for counters and bytes.
    #
    layout = '{:<12}  {:>20}     {:>20}     {:>20}     {:>20}     {:>20}'

    #
    # Port Requestor/Responder statistics.
    #
    try:
        request_metrics = oem_metrics['Request']
        response_metrics = oem_metrics['Response']

        print('Requestor/Responder Interface Statistics:')
        print()
        print(layout.format('', 'Xmit Count', 'Xmit Bytes', 'Recv Count', 'Recv Bytes', ''))
        print(layout.format('Requests',
                              request_metrics['XmitCount'],
                              request_metrics['XmitBytes'],
                              request_metrics['RecvCount'],
                              request_metrics['RecvBytes'],
                              ''))
        print(layout.format('Responses',
                              response_metrics['XmitCount'],
                              response_metrics['XmitBytes'],
                              response_metrics['RecvCount'],
                              response_metrics['RecvBytes'],
                              ''))

        print()
        print()
        print()
    except:
        pass

    #
    # Port VC statistics.
    #
    try:
        x = oem_metrics['VC0']['XmitCount'],

        print('Packet Relay Interface Statistics:')
        print()
        print(layout.format('', 'Xmit Packets', 'Xmit Bytes', 'Recv Packets', 'Recv Bytes', 'Occupancy'))

        for vc in range(16):
            vc_key = 'VC{}'.format(vc)
            print(layout.format(vc_key,
                                  oem_metrics[vc_key]['XmitCount'],
                                  oem_metrics[vc_key]['XmitBytes'],
                                  oem_metrics[vc_key]['RecvCount'],
                                  oem_metrics[vc_key]['RecvBytes'],
                                  oem_metrics[vc_key]['Occupancy']))
    except:
        pass

    return True

# ----------------------------------------------------------------------------------------------------------------------

def resolve(endpoint):

    #
    # An endpoint is of the form <name>:<int>/<int>.  The :<int> is optional.
    #
    name,delimiter,port_number = endpoint.partition('/')
    if not port_number:
        print('invalid endpoint [{}] specified'.format(endpoint))
        sys.exit(1)

    hostname,delimiter,hostport = name.partition(':')
    if not hostport:
        hostport = '8081'

    try:
        hostname = socket.gethostbyname(hostname)
    except:
        print('can\'t resolve the node address {}', name)
        sys.exit(0)

    return '{}:{}'.format(hostname, hostport), int(port_number)


if __name__ == '__main__':

    #
    # Get the command line parameters.
    #
    parser = argparse.ArgumentParser(description='port state manipulator', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-f', '--force',      help='force a transition',     required=False,  action='store_true')
    parser.add_argument('endpoint',           help=endpoint_help,                             metavar='Endpoint')
    parser.add_argument('command',            help=command_help,             nargs='*',       metavar='Command', choices=command_choices)

    args = vars(parser.parse_args())

    args['server'], port = resolve(args['endpoint'])

    #
    # Fetch the chassis attribute in order to determine the type of node.
    #
    status, chassis = rest_get(args['server'], '/redfish/v1/Chassis/1')
    if chassis == None:
        print('{} GET chassis failed'.format(args['endpoint']))
        sys.exit(1)

    #
    # Determine the attribute from the port number.
    #
    node_type = chassis['Oem']['Hpe']['NodeType']
    if node_type == 'Switch':
        attribute = 'redfish/v1/Fabrics/GenZ/Switches/Switch{}/Ports/{}'.format(1 + port//60, port%60)
    elif node_type == 'Compute':
        attribute = 'redfish/v1/Systems/1/FabricAdapters/1/Ports/{}'.format(port)
    elif node_type == 'Memory':
        attribute = 'redfish/v1/Fabrics/GenZ/Switches/Switch1/Ports/{}'.format(port)
    elif node_type == 'IO':
        attribute = 'redfish/v1/Systems/1/FabricAdapters/1/Ports/{}'.format(port)

    #
    # Do what the user requested.
    #
    for command in args['command']:
        if   command == 'metrics':
            port_metrics(args, attribute)
        elif command == 'up':
            port_up(args, attribute)
        elif command == 'down':
            port_down(args, attribute)
        elif command == 'reset':
            port_reset(args, attribute)
        elif command == 'query':
            port_query(args, attribute)

    sys.exit(0)

