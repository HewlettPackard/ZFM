#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

#
# Example calls:
#
# ./zfmcurl.py -s 192.168.1.240:31000                -f GET    Fabrics/GenZ/Switches/1/Ports/1/LPRT/2
# ./zfmcurl.py -s 192.168.1.240:31000 -i input.post  -f POST   Fabrics/GenZ/Switches/1/Ports/1/LPRT
# ./zfmcurl.py -s 192.168.1.240:31000 -i input.patch -f PATCH  Fabrics/GenZ/Switches/1/Ports/1/LPRT/5
# ./zfmcurl.py -s 192.168.1.240:31000                -f DELETE Fabrics/GenZ/Switches/1/Ports/1/LPRT/3
#


import os
import sys
import json
import argparse
import subprocess

headers = '-H "Accept: application/json" -H "Content-Type: application/json"'
actions = [ 'GET', 'POST', 'PATCH', 'DELETE']

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    #
    # Get the command line parameters.
    #
    parser = argparse.ArgumentParser(description='zfm simulator curl tool')

    parser.add_argument('-i', '--input',    help='input filename',                 required=False)
    parser.add_argument('-f', '--function', help='REST function',                  required=True)
    parser.add_argument('-s', '--server',   help='server address',                 required=False)
    parser.add_argument('attribute',        help='attribute to perform action on')

    args = vars(parser.parse_args())

    if ':' not in args['server']:
        args['server'] += ':8081'

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
    # Get the input if needed.
    #
    input = ''
    if args['input']:
        input = '-d @{}'.format(args['input'])

    #
    # Send the curl command to the server.
    #
    curl_command = 'curl -i {headers} -X {function} {input} http://{server}/{attribute}'.format(headers=headers,
                                                                                                function=function,
                                                                                                input=input,
                                                                                                server=args['server'],
                                                                                                attribute=attribute)

    subprocess.call(curl_command, shell=True)
