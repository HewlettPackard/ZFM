#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import os
import sys
import json
import socket
import argparse
import requests
import textwrap

from http import HTTPStatus

# ----------------------------------------------------------------------------------------------------------------------

def resolve(hostname):
    if not hostname:
        try:
            hostname = os.environ['ZFM']
        except:
            print('can\'t find the ZFM server')
            sys.exit(0)

    hostname, delimieter, hostport = hostname.partition(':')
    if not hostport: hostport = '60000'

    try:
        hostname = socket.gethostbyname(hostname)
    except:
        print('can\'t resolve the ZFM server address')
        sys.exit(0)

    return '{}:{}'.format(hostname, hostport)

# ----------------------------------------------------------------------------------------------------------------------

def zfm_request(url):
    #
    # Send the REST command to the server.
    #
    headers = { "Accept": "text/html", "Content-Type": "text/html" }

    try:
        r = requests.get(url, headers=headers)
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

    reply = r.text if (status//100) == 2 else None
    return status, reply

# ----------------------------------------------------------------------------------------------------------------------

def zfm_fabric(args, parameters):
    url = 'http://{}?{}'.format(args['server_address'], '&'.join(parameters))
    return zfm_request(url)

# ----------------------------------------------------------------------------------------------------------------------

def zfm_node(args, parameters):
    url = 'http://{}/{}?{}'.format(args['server_address'], args['node'], '&'.join(parameters))
    return zfm_request(url)

# ----------------------------------------------------------------------------------------------------------------------

def zfm_port(args, parameters):
    url = 'http://{}/{}/{}?{}'.format(args['server_address'], args['node'], args['port'], '&'.join(parameters))
    return zfm_request(url)

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    #
    # Get the command line parameters.
    #
    epilog=textwrap.dedent("""\
limitations: -f and -n are mutually exclusive
             -f and -p are mutually exclusive
             -t can only be specified with -f
             -p can only be specified with -n""")

    parser = argparse.ArgumentParser(description='Gen-Z fabric manager information',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=epilog)

    parser.add_argument('-o', '--output',     help='output file')
    parser.add_argument('-j', '--json',       help='output formatted as JSON',                 required=False,  action='store_true')
    parser.add_argument('-c', '--configured', help='configured entities only',                                  action='store_true')
    parser.add_argument('-e', '--enabled',    help='enabled entities only',                                     action='store_true')
    parser.add_argument('-t', '--type',       help='types to query')
    parser.add_argument('-f', '--fabric',     help='fabric view (default)',                                     action='store_true')
    parser.add_argument('-n', '--node',       help='node name')
    parser.add_argument('-p', '--port',       help='port number')
    parser.add_argument('server',             help='Gen-Z fabric manager server IP address',                    nargs='?', metavar='ZFM management address')

    args = vars(parser.parse_args())

    if args['fabric'] and args['node']:
        print('-f and -n are mutually exclusive')
        sys.exit(0)
    elif args['fabric'] and args['port']:
        print('-f and -p are mutually exclusive')
        sys.exit(0)
    elif args['port'] and not args['node']:
        print('-p can only be specified with -n')
        sys.exit(0)

    args['format'] = 'JSON' if args['json'] else 'ASCII'

    if not args['fabric'] and not args['node']:
        args['fabric'] = True

    if args['type'] and not args['fabric']:
        print('-t can only be specified with -f')
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

    #
    # Get the server address.
    #
    args['server_address'] = resolve(args['server'])

    #
    # Setup the URL parameters
    #
    parameters = ['format={}'.format(args['format'])]
    if args['enabled']:
        parameters.append('interface=Enabled')
    if args['configured']:
        parameters.append('config=Enabled')
    if args['type']:
        parameters.append('type={}'.format(args['type']))

    #
    # Get the information.
    #
    try:
        if args['fabric']:
            status, data = zfm_fabric(args, parameters)
        elif args['node'] and not args['port']:
            status, data = zfm_node(args, parameters)
        elif args['node'] and args['port']:
            status, data = zfm_port(args, parameters)
    except KeyboardInterrupt:
        sys.exit(1)

    #
    # Display the results
    #
    if status != 200:
        print('request returned an error {}'.format(status))
        sys.exit(1)

    print(data)
