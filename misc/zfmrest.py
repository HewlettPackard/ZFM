#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

#
# Example calls:
#
# ./zfmrest.py -s 192.168.1.240:31000                -f GET    Fabrics/GenZ/Switches/1/Ports/1/LPRT/2
# ./zfmrest.py -s 192.168.1.240:31000 -i input.post  -f POST   Fabrics/GenZ/Switches/1/Ports/1/LPRT/8
# ./zfmrest.py -s 192.168.1.240:31000 -i input.patch -f PATCH  Fabrics/GenZ/Switches/1/Ports/1/LPRT/5
# ./zfmrest.py -s 192.168.1.240:31000                -f DELETE Fabrics/GenZ/Switches/1/Ports/1/LPRT/3
#


import os
import sys
import json
import socket
import argparse
import requests

actions = { 'GET': requests.get, 'POST': requests.post, 'PATCH': requests.patch, 'DELETE': requests.delete }

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

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    #
    # Get the command line parameters.
    #
    parser = argparse.ArgumentParser(description='zfm simulator rest tool')

    parser.add_argument('-i', '--input',    help='input filename',                 required=False)
    parser.add_argument('-f', '--function', help='REST function',                  required=True)
    parser.add_argument('-s', '--server',   help='server address',                 required=False)
    parser.add_argument('attribute',        help='attribute to perform action on')

    args = vars(parser.parse_args())
    args['server_address'] = resolve(args['server'])

    #
    # Test the function to be sure that we understand it.
    #
    function = args['function'].upper()
    if function not in actions:
        print('unknown function specified')
        sys.exit(0)

    #
    # Fix the attribute if needed.
    #
    attribute = args['attribute']
    if not attribute.startswith('/redfish/v1'):
        attribute = 'redfish/v1/{}'.format(attribute)

    #
    # Load the input file (if specified)
    #
    payload = ''
    if args['input']:
        with open(args['input']) as f:
            payload = f.read()

    #
    # Send the REST command to the server.
    #
    headers = { "Accept": "application/json", "Content-Type": "application/json" }
    url = 'http://{server}/{attribute}'.format(server=args['server_address'], attribute=attribute)

    r = actions[function](url, data=payload, headers=headers)

    #
    # Print the status code and the payload.
    #
    print(r.status_code)
    print(r.text)
